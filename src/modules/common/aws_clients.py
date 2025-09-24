"""
AWS 클라이언트 관리
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSConfig:
    """AWS 설정"""

    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        # Bedrock 설정
        self.bedrock_model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-sonnet-20240229-v1:0"
        )
        self.knowledge_base_id = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")

        # S3 설정
        self.s3_bucket_name = os.getenv("S3_BUCKET_NAME", "persona-welfare-studio")


class S3Client:
    """S3 클라이언트"""

    def __init__(self, config: AWSConfig = None):
        self.config = config or AWSConfig()
        self.s3_client = boto3.client(
            's3',
            region_name=self.config.region,
            aws_access_key_id=self.config.access_key_id,
            aws_secret_access_key=self.config.secret_access_key
        )

    def upload_knowledge_files(self, task_id: str, file_paths: List[str]) -> Dict[str, Any]:
        """도메인 지식 파일들을 S3에 업로드"""
        try:
            uploaded_files = []
            failed_files = []

            # 태스크별 S3 폴더 생성
            s3_prefix = f"knowledge-base/{task_id}/"

            for file_path in file_paths:
                if not os.path.exists(file_path):
                    failed_files.append({
                        "file_path": file_path,
                        "error": "파일이 존재하지 않습니다"
                    })
                    continue

                try:
                    # S3 키 생성
                    filename = os.path.basename(file_path)
                    s3_key = f"{s3_prefix}{filename}"

                    # 파일 업로드
                    with open(file_path, 'rb') as file:
                        self.s3_client.upload_fileobj(
                            file,
                            self.config.s3_bucket_name,
                            s3_key,
                            ExtraArgs={
                                'Metadata': {
                                    'task_id': task_id,
                                    'original_filename': filename
                                }
                            }
                        )

                    uploaded_files.append({
                        "local_path": file_path,
                        "s3_key": s3_key,
                        "s3_url": f"s3://{self.config.s3_bucket_name}/{s3_key}",
                        "filename": filename,
                        "size": os.path.getsize(file_path)
                    })

                    logger.info(f"S3 업로드 성공: {s3_key}")

                except ClientError as e:
                    logger.error(f"S3 업로드 실패: {file_path}, 에러: {e}")
                    failed_files.append({
                        "file_path": file_path,
                        "error": str(e)
                    })

            result = {
                "task_id": task_id,
                "s3_prefix": s3_prefix,
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "success_count": len(uploaded_files),
                "fail_count": len(failed_files)
            }

            logger.info(f"S3 업로드 완료: {len(uploaded_files)}개 성공, {len(failed_files)}개 실패")
            return result

        except Exception as e:
            logger.error(f"S3 업로드 전체 실패: {e}")
            raise

    def file_exists(self, s3_key: str) -> bool:
        """S3 파일 존재 여부 확인"""
        try:
            self.s3_client.head_object(Bucket=self.config.s3_bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False


class BedrockClient:
    """Bedrock 클라이언트"""

    def __init__(self, config: AWSConfig = None):
        self.config = config or AWSConfig()

        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=self.config.region,
            aws_access_key_id=self.config.access_key_id,
            aws_secret_access_key=self.config.secret_access_key
        )

        # Knowledge Base용 클라이언트 (있을 경우)
        if self.config.knowledge_base_id:
            try:
                self.bedrock_agent_runtime = boto3.client(
                    'bedrock-agent-runtime',
                    region_name=self.config.region,
                    aws_access_key_id=self.config.access_key_id,
                    aws_secret_access_key=self.config.secret_access_key
                )
            except Exception as e:
                logger.warning(f"Bedrock Agent Runtime 초기화 실패: {e}")
                self.bedrock_agent_runtime = None
        else:
            self.bedrock_agent_runtime = None

    def invoke_model(self, prompt: str, max_tokens: int = 2000) -> str:
        """Claude 모델 직접 호출"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=self.config.bedrock_model_id,
                body=json.dumps(body),
                contentType='application/json'
            )

            response_body = json.loads(response['body'].read())

            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']
            else:
                logger.warning("Bedrock 응답에서 텍스트를 찾을 수 없습니다")
                return ""

        except ClientError as e:
            logger.error(f"Bedrock 모델 호출 실패: {e}")
            raise
        except Exception as e:
            logger.error(f"Bedrock 모델 호출 중 예외 발생: {e}")
            raise

    def retrieve_and_generate(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """RAG 검색 및 생성 (Knowledge Base 사용)"""
        try:
            # Knowledge Base가 없으면 일반 모델 호출
            if not self.config.knowledge_base_id or not self.bedrock_agent_runtime:
                logger.warning("Knowledge Base ID가 없음, 일반 모델 호출로 대체")
                response_text = self.invoke_model(query)
                return {
                    "output": {"text": response_text},
                    "retrievalResults": [],
                    "source_references": []
                }

            # 전체 프롬프트 구성
            full_prompt = query
            if context:
                full_prompt = f"컨텍스트: {context}\n\n질문: {query}"

            # RAG 호출
            response = self.bedrock_agent_runtime.retrieve_and_generate(
                input={'text': full_prompt},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.config.knowledge_base_id,
                        'modelArn': f"arn:aws:bedrock:{self.config.region}::foundation-model/{self.config.bedrock_model_id}",
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': 10
                            }
                        }
                    }
                }
            )

            # 응답 처리
            output_text = response.get('output', {}).get('text', '')
            retrieval_results = response.get('retrievalResults', [])

            # 소스 참조 정보 추출
            source_references = []
            for result in retrieval_results:
                source_info = {
                    'content': result.get('content', {}).get('text', ''),
                    'score': result.get('score', 0.0),
                    'location': result.get('location', {})
                }
                source_references.append(source_info)

            logger.info(f"RAG 응답 생성: {len(output_text)} 문자, {len(source_references)}개 소스")

            return {
                "output": {"text": output_text},
                "retrievalResults": retrieval_results,
                "source_references": source_references
            }

        except ClientError as e:
            logger.error(f"RAG 호출 실패: {e}")
            # Knowledge Base 호출 실패시 일반 모델로 대체
            try:
                response_text = self.invoke_model(query)
                return {
                    "output": {"text": response_text},
                    "retrievalResults": [],
                    "source_references": []
                }
            except:
                raise e
        except Exception as e:
            logger.error(f"RAG 호출 중 예외 발생: {e}")
            raise

    def retrieve_documents(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Knowledge Base에서 문서 검색만 수행"""
        try:
            if not self.config.knowledge_base_id or not self.bedrock_agent_runtime:
                logger.warning("Knowledge Base ID가 설정되지 않음")
                return []

            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.config.knowledge_base_id,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results
                    }
                }
            )

            retrieved_docs = []
            for result in response.get('retrievalResults', []):
                doc_info = {
                    'content': result.get('content', {}).get('text', ''),
                    'score': result.get('score', 0.0),
                    'location': result.get('location', {}),
                    'metadata': result.get('metadata', {})
                }
                retrieved_docs.append(doc_info)

            logger.info(f"문서 검색 완료: {len(retrieved_docs)}개 문서")
            return retrieved_docs

        except ClientError as e:
            logger.error(f"문서 검색 실패: {e}")
            return []
        except Exception as e:
            logger.error(f"문서 검색 중 예외 발생: {e}")
            return []


# 전역 클라이언트 인스턴스들
aws_config = AWSConfig()
s3_client = S3Client(aws_config)
bedrock_client = BedrockClient(aws_config)