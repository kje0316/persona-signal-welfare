# -*- coding: utf-8 -*-
"""
api_service.py
페르소나 생성 엔진의 API 서비스 연동 모듈
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .persona_generator import PersonaGenerator, PersonaProfile
from .rag_storyteller import RAGKnowledgeBase, PersonaStoryTeller, PersonaStory

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonaAPIService:
    """페르소나 생성 시스템의 API 서비스 래퍼"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()

        # 경로 설정
        self.data_path = Path(self.config['data_analysis_path'])
        self.kb_path = Path(self.config['knowledge_base_path'])
        self.output_path = Path(self.config['output_path'])

        # 캐시 설정
        self.personas_cache = {}
        self.stories_cache = {}
        self.last_generated = None

        # 컴포넌트 초기화
        self.generator = None
        self.storyteller = None
        self._initialize_components()

    def _load_default_config(self) -> Dict[str, Any]:
        """기본 설정 로드"""
        project_root = Path(__file__).parent.parent.parent.parent

        return {
            'data_analysis_path': str(project_root / 'src' / 'modules' / 'data_analysis'),
            'knowledge_base_path': str(project_root / 'src' / 'modules' / 'data_analysis' / 'rag_aug_out' / 'kb_chunks.jsonl'),
            'policy_docs_path': str(project_root / 'src' / 'data' / 'documents'),
            'output_path': str(project_root / 'src' / 'data' / 'generated'),
            'cache_duration_hours': 24,
            'default_persona_count': 5
        }

    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            # 페르소나 생성기 초기화
            kb_path = self.kb_path if self.kb_path.exists() else None
            self.generator = PersonaGenerator(
                data_analysis_path=str(self.data_path),
                knowledge_base_path=str(kb_path) if kb_path else None
            )

            # RAG 지식 베이스 및 스토리텔러 초기화
            knowledge_base = RAGKnowledgeBase(
                kb_chunks_path=str(kb_path) if kb_path else None,
                policy_docs_path=self.config.get('policy_docs_path')
            )
            self.storyteller = PersonaStoryTeller(knowledge_base)

            logger.info("🚀 PersonaAPIService 초기화 완료")

        except Exception as e:
            logger.error(f"❌ 컴포넌트 초기화 실패: {e}")
            raise

    def _is_cache_valid(self) -> bool:
        """캐시 유효성 검사"""
        if not self.last_generated:
            return False

        cache_duration = self.config['cache_duration_hours'] * 3600
        elapsed = (datetime.now() - self.last_generated).total_seconds()
        return elapsed < cache_duration

    async def generate_personas_async(self, n_personas: int = None, force_regenerate: bool = False) -> List[PersonaProfile]:
        """비동기 페르소나 생성"""
        n_personas = n_personas or self.config['default_persona_count']

        # 캐시 확인
        if not force_regenerate and self._is_cache_valid() and self.personas_cache:
            logger.info("📦 캐시된 페르소나 반환")
            return list(self.personas_cache.values())

        logger.info(f"🔄 {n_personas}개 페르소나 생성 시작...")

        try:
            # 비동기로 페르소나 생성
            loop = asyncio.get_event_loop()
            personas = await loop.run_in_executor(
                None,
                self.generator.generate_personas,
                n_personas
            )

            # 캐시 업데이트
            self.personas_cache = {persona.id: persona for persona in personas}
            self.last_generated = datetime.now()

            # 파일 저장
            output_file = self.output_path / 'generated_personas.json'
            self.output_path.mkdir(parents=True, exist_ok=True)
            self.generator.save_personas(personas, str(output_file))

            logger.info(f"✅ {len(personas)}개 페르소나 생성 완료")
            return personas

        except Exception as e:
            logger.error(f"❌ 페르소나 생성 실패: {e}")
            raise

    def generate_personas(self, n_personas: int = None, force_regenerate: bool = False) -> List[PersonaProfile]:
        """동기 페르소나 생성 (호환성을 위한 래퍼)"""
        return asyncio.run(self.generate_personas_async(n_personas, force_regenerate))

    async def generate_stories_async(self, persona_ids: Optional[List[int]] = None) -> List[PersonaStory]:
        """비동기 페르소나 스토리 생성"""
        # 페르소나가 없으면 먼저 생성
        if not self.personas_cache:
            await self.generate_personas_async()

        # 특정 ID만 생성하거나 모든 페르소나 스토리 생성
        target_personas = []
        if persona_ids:
            target_personas = [self.personas_cache[pid] for pid in persona_ids if pid in self.personas_cache]
        else:
            target_personas = list(self.personas_cache.values())

        logger.info(f"📝 {len(target_personas)}개 페르소나 스토리 생성 시작...")

        try:
            stories = []
            for persona in target_personas:
                # 캐시 확인
                if persona.id in self.stories_cache and self._is_cache_valid():
                    stories.append(self.stories_cache[persona.id])
                    continue

                # 스토리 생성
                loop = asyncio.get_event_loop()
                story = await loop.run_in_executor(
                    None,
                    self.storyteller.create_persona_story,
                    persona.__dict__
                )

                stories.append(story)
                self.stories_cache[persona.id] = story

            # 파일 저장
            stories_file = self.output_path / 'persona_stories.json'
            stories_dict = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_stories': len(stories),
                    'storyteller_version': '1.0'
                },
                'stories': [story.__dict__ for story in stories]
            }

            with open(stories_file, 'w', encoding='utf-8') as f:
                json.dump(stories_dict, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ {len(stories)}개 스토리 생성 완료")
            return stories

        except Exception as e:
            logger.error(f"❌ 스토리 생성 실패: {e}")
            raise

    def generate_stories(self, persona_ids: Optional[List[int]] = None) -> List[PersonaStory]:
        """동기 스토리 생성 (호환성을 위한 래퍼)"""
        return asyncio.run(self.generate_stories_async(persona_ids))

    def get_persona_by_id(self, persona_id: int) -> Optional[PersonaProfile]:
        """ID로 특정 페르소나 조회"""
        return self.personas_cache.get(persona_id)

    def get_story_by_persona_id(self, persona_id: int) -> Optional[PersonaStory]:
        """페르소나 ID로 스토리 조회"""
        return self.stories_cache.get(persona_id)

    def get_personas_by_criteria(self, **criteria) -> List[PersonaProfile]:
        """조건에 맞는 페르소나 필터링"""
        results = []
        for persona in self.personas_cache.values():
            match = True

            for key, value in criteria.items():
                if hasattr(persona, key):
                    persona_value = getattr(persona, key)
                    if isinstance(persona_value, str) and isinstance(value, str):
                        if value.lower() not in persona_value.lower():
                            match = False
                            break
                    elif persona_value != value:
                        match = False
                        break
                else:
                    match = False
                    break

            if match:
                results.append(persona)

        return results

    def get_welfare_recommendations(self, persona_id: int) -> Dict[str, Any]:
        """특정 페르소나의 복지 서비스 추천"""
        persona = self.get_persona_by_id(persona_id)
        if not persona:
            return {'error': 'Persona not found'}

        return {
            'persona_id': persona_id,
            'name': persona.name,
            'primary_needs': [need for need, score in persona.welfare_needs.items() if score > 0.6],
            'recommended_services': persona.recommended_services,
            'risk_factors': persona.risk_factors,
            'confidence_score': persona.confidence_score
        }

    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 정보"""
        return {
            'service_status': 'active',
            'personas_cached': len(self.personas_cache),
            'stories_cached': len(self.stories_cache),
            'last_generated': self.last_generated.isoformat() if self.last_generated else None,
            'cache_valid': self._is_cache_valid(),
            'config': {
                'data_path': str(self.data_path),
                'kb_path': str(self.kb_path),
                'output_path': str(self.output_path)
            }
        }

    def clear_cache(self):
        """캐시 초기화"""
        self.personas_cache.clear()
        self.stories_cache.clear()
        self.last_generated = None
        logger.info("🧹 캐시 초기화 완료")

# FastAPI 통합을 위한 헬퍼 함수들
def create_fastapi_routes(app, service: PersonaAPIService):
    """FastAPI 앱에 라우트 추가"""

    @app.get("/api/v1/personas")
    async def get_personas(n_personas: int = 5, force_regenerate: bool = False):
        """페르소나 목록 조회/생성"""
        try:
            personas = await service.generate_personas_async(n_personas, force_regenerate)
            return {
                'success': True,
                'data': [persona.__dict__ for persona in personas],
                'count': len(personas)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @app.get("/api/v1/personas/{persona_id}")
    async def get_persona(persona_id: int):
        """특정 페르소나 조회"""
        persona = service.get_persona_by_id(persona_id)
        if persona:
            return {'success': True, 'data': persona.__dict__}
        else:
            return {'success': False, 'error': 'Persona not found'}

    @app.get("/api/v1/stories")
    async def get_stories(persona_ids: Optional[str] = None):
        """페르소나 스토리 조회/생성"""
        try:
            ids = None
            if persona_ids:
                ids = [int(x) for x in persona_ids.split(',')]

            stories = await service.generate_stories_async(ids)
            return {
                'success': True,
                'data': [story.__dict__ for story in stories],
                'count': len(stories)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @app.get("/api/v1/personas/{persona_id}/recommendations")
    async def get_recommendations(persona_id: int):
        """복지 서비스 추천"""
        result = service.get_welfare_recommendations(persona_id)
        if 'error' in result:
            return {'success': False, 'error': result['error']}
        else:
            return {'success': True, 'data': result}

    @app.get("/api/v1/system/status")
    async def get_system_status():
        """시스템 상태 확인"""
        status = service.get_system_status()
        return {'success': True, 'data': status}

    @app.post("/api/v1/system/clear-cache")
    async def clear_cache():
        """캐시 초기화"""
        service.clear_cache()
        return {'success': True, 'message': 'Cache cleared'}

def main():
    """CLI 테스트 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="PersonaAPIService 테스트")
    parser.add_argument("--config", help="설정 파일 경로 (JSON)")
    parser.add_argument("--personas", type=int, default=3, help="생성할 페르소나 수")
    parser.add_argument("--stories", action="store_true", help="스토리도 생성")

    args = parser.parse_args()

    # 설정 로드
    config = None
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)

    # 서비스 초기화
    print("🚀 PersonaAPIService 초기화 중...")
    service = PersonaAPIService(config)

    # 페르소나 생성
    print(f"👥 {args.personas}개 페르소나 생성 중...")
    personas = service.generate_personas(args.personas)

    print(f"✅ 생성 완료: {len(personas)}개")
    for persona in personas:
        print(f"  - {persona.name} ({persona.age_group}, {persona.district})")

    # 스토리 생성 (옵션)
    if args.stories:
        print("\n📖 스토리 생성 중...")
        stories = service.generate_stories()
        print(f"✅ 스토리 생성 완료: {len(stories)}개")

        # 첫 번째 스토리 샘플 출력
        if stories:
            sample = stories[0]
            print(f"\n📝 샘플 스토리 - {sample.character_name}:")
            print(f"   배경: {sample.background_story[:100]}...")

    # 시스템 상태 출력
    print(f"\n🔍 시스템 상태:")
    status = service.get_system_status()
    print(f"  캐시된 페르소나: {status['personas_cached']}개")
    print(f"  캐시된 스토리: {status['stories_cached']}개")

if __name__ == "__main__":
    main()