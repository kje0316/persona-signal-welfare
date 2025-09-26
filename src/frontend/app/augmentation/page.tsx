'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Upload, FileText, Database, Bot, CheckCircle, XCircle, Loader2, Download } from 'lucide-react'

const API_URL = 'http://localhost:8001'

interface TaskStatus {
  task_id: string
  status: string
  progress: number
  current_stage: string
  message?: string
  results?: any
  error?: string
  started_at?: string
  estimated_completion?: string
}

interface UploadResponse {
  success: boolean
  file_id?: string
  batch_id?: string
  filename?: string
  file_path?: string
  files?: any[]
  message: string
}

export default function AugmentationPage() {
  const [structuredFile, setStructuredFile] = useState<File | null>(null)
  const [knowledgeFiles, setKnowledgeFiles] = useState<File[]>([])
  const [structuredFileId, setStructuredFileId] = useState<string>('')
  const [knowledgeFilePaths, setKnowledgeFilePaths] = useState<string[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>('')
  const [taskId, setTaskId] = useState<string>('')
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  // WebSocket 제거 - 프로토타입에서는 클라이언트 사이드 시뮬레이션 사용

  // 정형 데이터 파일 업로드 (프로토타입 시뮬레이션)
  const handleStructuredFileUpload = async () => {
    if (!structuredFile) return

    setIsUploading(true)
    setUploadStatus('정형 데이터 업로드 중...')

    // 시연용 2초 시뮬레이션
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Mock 성공 응답
    setStructuredFileId(`uploaded_structured_${Date.now()}.csv`)
    setUploadStatus('정형 데이터 업로드 완료!')
    setIsUploading(false)
  }

  // 지식 파일들 업로드 (프로토타입 시뮬레이션)
  const handleKnowledgeFilesUpload = async () => {
    if (knowledgeFiles.length === 0) return

    setIsUploading(true)
    setUploadStatus('지식 파일들 업로드 중...')

    // 시연용 2초 시뮬레이션
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Mock 성공 응답
    const mockPaths = knowledgeFiles.map((file, index) => `uploaded_knowledge_${index}_${Date.now()}.txt`)
    setKnowledgeFilePaths(mockPaths)
    setUploadStatus(`지식 파일들 업로드 완료! (${knowledgeFiles.length}개 파일)`)
    setIsUploading(false)
  }

  // 데이터 증강 시작 (프로토타입 버전 - 가짜 진행률)
  const startAugmentation = async () => {
    if (!structuredFileId || knowledgeFilePaths.length === 0) {
      alert('파일을 먼저 업로드해주세요.')
      return
    }

    setIsProcessing(true)

    // 가짜 task ID 생성
    const fakeTaskId = 'demo-' + Date.now()
    setTaskId(fakeTaskId)

    // 프로그레스 시뮬레이션 단계들
    const stages = [
      { progress: 0, stage: '시작', message: '데이터 증강을 시작합니다...' },
      { progress: 20, stage: '데이터 전처리', message: '데이터 형식을 분석하고 있습니다...' },
      { progress: 40, stage: '페르소나 생성', message: 'AI 페르소나를 생성하고 있습니다...' },
      { progress: 60, stage: '데이터 증강', message: '데이터를 증강하고 있습니다...' },
      { progress: 80, stage: '품질 평가', message: '결과를 평가하고 있습니다...' },
      { progress: 100, stage: '완료', message: '모든 작업이 완료되었습니다!' }
    ]

    // 각 단계를 1.5초씩 진행 (총 9초)
    for (let i = 0; i < stages.length; i++) {
      const stage = stages[i]
      setTaskStatus({
        task_id: fakeTaskId,
        status: stage.progress === 100 ? 'completed' : 'running',
        progress: stage.progress,
        current_stage: stage.stage,
        message: stage.message,
        results: stage.progress === 100 ? {
          personas_count: 4,
          augmented_samples: 2500,
          quality_score: 0.87
        } : undefined
      })

      if (i < stages.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 1500)) // 1.5초 대기
      }
    }

    setIsProcessing(false)
  }

  // 결과 다운로드
  const downloadResults = async (fileType: string) => {
    if (!taskId) return

    try {
      const response = await fetch(`${API_URL}/api/v1/augmentation/download/${taskId}/${fileType}`)

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${fileType}_${taskId}.${fileType === 'augmented_data' ? 'csv' : 'json'}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else {
        alert('다운로드 실패')
      }
    } catch (error) {
      alert('다운로드 오류: ' + (error instanceof Error ? error.message : '알 수 없는 오류'))
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600'
      case 'failed': return 'text-red-600'
      case 'running': return 'text-blue-600'
      default: return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'failed': return <XCircle className="w-5 h-5 text-red-600" />
      case 'running': return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
      default: return <div className="w-5 h-5 rounded-full bg-gray-300"></div>
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          🤖 AI 페르소나 기반 데이터 증강
        </h1>
        <p className="text-xl text-gray-600">
          구조화된 데이터와 도메인 지식을 업로드하여 AI 페르소나를 생성하고 데이터를 증강하세요
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8 mb-8">
        {/* 정형 데이터 업로드 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="w-5 h-5" />
              정형 데이터 업로드
            </CardTitle>
            <CardDescription>
              CSV, Excel 파일을 업로드하세요
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="structured-file">파일 선택</Label>
              <Input
                id="structured-file"
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(e) => setStructuredFile(e.target.files?.[0] || null)}
              />
            </div>
            {structuredFile && (
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                <span className="text-sm">{structuredFile.name}</span>
              </div>
            )}
            <Button
              onClick={handleStructuredFileUpload}
              disabled={!structuredFile || isUploading}
              className="w-full"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  업로드 중...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  업로드
                </>
              )}
            </Button>
            {structuredFileId && (
              <Badge variant="secondary" className="w-full justify-center">
                업로드 완료
              </Badge>
            )}
          </CardContent>
        </Card>

        {/* 지식 파일 업로드 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="w-5 h-5" />
              도메인 지식 파일 업로드
            </CardTitle>
            <CardDescription>
              TXT, MD, PDF, DOCX 파일들을 업로드하세요
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="knowledge-files">파일 선택 (여러개 가능)</Label>
              <Input
                id="knowledge-files"
                type="file"
                multiple
                accept=".txt,.md,.pdf,.docx"
                onChange={(e) => setKnowledgeFiles(Array.from(e.target.files || []))}
              />
            </div>
            {knowledgeFiles.length > 0 && (
              <div className="space-y-2">
                {knowledgeFiles.map((file, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    <span className="text-sm">{file.name}</span>
                  </div>
                ))}
              </div>
            )}
            <Button
              onClick={handleKnowledgeFilesUpload}
              disabled={knowledgeFiles.length === 0 || isUploading}
              className="w-full"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  업로드 중...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  업로드
                </>
              )}
            </Button>
            {knowledgeFilePaths.length > 0 && (
              <Badge variant="secondary" className="w-full justify-center">
                {knowledgeFilePaths.length}개 파일 업로드 완료
              </Badge>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 업로드 상태 */}
      {uploadStatus && (
        <Card className="mb-8">
          <CardContent className="pt-6">
            <p className="text-center text-gray-700">{uploadStatus}</p>
          </CardContent>
        </Card>
      )}

      {/* 데이터 증강 시작 */}
      <Card className="mb-8">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">데이터 증강 실행</CardTitle>
          <CardDescription>
            업로드된 파일들을 바탕으로 AI 페르소나를 생성하고 데이터를 증강합니다
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <Button
            onClick={startAugmentation}
            disabled={!structuredFileId || knowledgeFilePaths.length === 0 || isProcessing}
            size="lg"
            className="px-8 py-4"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                처리 중...
              </>
            ) : (
              <>
                <Bot className="w-5 h-5 mr-2" />
                데이터 증강 시작
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* 진행 상황 */}
      {taskStatus && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {getStatusIcon(taskStatus.status)}
              진행 상황
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium">작업 ID: {taskStatus.task_id}</span>
                <span className={`text-sm font-medium ${getStatusColor(taskStatus.status)}`}>
                  {taskStatus.status}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${taskStatus.progress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-600 mt-2">
                {taskStatus.progress}% - {taskStatus.current_stage}
              </p>
              {taskStatus.message && (
                <p className="text-sm text-gray-500">{taskStatus.message}</p>
              )}
            </div>

            {taskStatus.error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded">
                <p className="text-red-600">{taskStatus.error}</p>
              </div>
            )}

            {taskStatus.status === 'completed' && (
              <div className="space-y-6">
                {/* 완료 메시지 */}
                <div className="p-6 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                    <div>
                      <h3 className="text-xl font-bold text-green-700">🎉 데이터 증강 완료!</h3>
                      <p className="text-green-600">4개의 고유한 페르소나가 생성되었고, 2,500개의 증강 데이터가 생성되었습니다.</p>
                    </div>
                  </div>
                </div>

                {/* 성능 개선 대시보드 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      📊 증강 전후 성능 비교
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                      <div className="text-center p-4 bg-red-50 rounded-lg">
                        <div className="text-2xl font-bold text-red-600">72%</div>
                        <div className="text-sm text-red-700">증강 전 정확도</div>
                      </div>
                      <div className="text-center p-4 bg-green-50 rounded-lg">
                        <div className="text-2xl font-bold text-green-600">87%</div>
                        <div className="text-sm text-green-700">증강 후 정확도</div>
                      </div>
                      <div className="text-center p-4 bg-blue-50 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600">+20.8%</div>
                        <div className="text-sm text-blue-700">성능 향상</div>
                      </div>
                    </div>

                    {/* 세부 지표 */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <h4 className="font-medium mb-2">주요 개선사항</h4>
                        <ul className="space-y-1 text-gray-600">
                          <li>• 데이터 커버리지: +40.0%</li>
                          <li>• F1 점수: +24.6%</li>
                          <li>• 리콜: +25.4%</li>
                        </ul>
                      </div>
                      <div>
                        <h4 className="font-medium mb-2">품질 지표</h4>
                        <ul className="space-y-1 text-gray-600">
                          <li>• 다양성: 92%</li>
                          <li>• 일관성: 89%</li>
                          <li>• 유효성: 85%</li>
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 생성된 페르소나 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      👥 생성된 페르소나 (4명)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-4 border rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-8 h-8 bg-pink-100 rounded-full flex items-center justify-center">
                            <span className="text-pink-600">👩</span>
                          </div>
                          <h4 className="font-medium">김영희 (20대 직장인)</h4>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">서울 거주, 사무직, 연봉 2800만원</p>
                        <div className="text-xs text-blue-600 bg-blue-50 p-2 rounded">
                          주요 니즈: 청년 월세 지원, 심리상담 서비스
                        </div>
                      </div>

                      <div className="p-4 border rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <span className="text-blue-600">👨</span>
                          </div>
                          <h4 className="font-medium">박민수 (30대 신혼부부)</h4>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">경기도 거주, 기술직, 연봉 4200만원</p>
                        <div className="text-xs text-green-600 bg-green-50 p-2 rounded">
                          주요 니즈: 신혼부부 전세자금, 출산장려금
                        </div>
                      </div>

                      <div className="p-4 border rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                            <span className="text-purple-600">👵</span>
                          </div>
                          <h4 className="font-medium">이순자 (60대 노인)</h4>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">부산 거주, 무직, 기초연금 120만원</p>
                        <div className="text-xs text-purple-600 bg-purple-50 p-2 rounded">
                          주요 니즈: 기초연금, 노인 돌봄 서비스
                        </div>
                      </div>

                      <div className="p-4 border rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                            <span className="text-orange-600">🎓</span>
                          </div>
                          <h4 className="font-medium">최지민 (대학생)</h4>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">대전 거주, 학생, 무소득</p>
                        <div className="text-xs text-orange-600 bg-orange-50 p-2 rounded">
                          주요 니즈: 국가장학금, 청년 구직활동 지원금
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 다운로드 버튼들 */}
                <Card>
                  <CardHeader>
                    <CardTitle>📥 결과 다운로드</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Button
                        variant="outline"
                        onClick={() => downloadResults('personas')}
                        className="flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        페르소나 JSON
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => downloadResults('augmented_data')}
                        className="flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        증강 데이터 CSV
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => downloadResults('evaluation_report')}
                        className="flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        평가 보고서
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => downloadResults('evaluation_results')}
                        className="flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        성능 지표
                      </Button>
                    </div>

                    <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                      <h4 className="font-medium text-blue-800 mb-2">🔍 핵심 인사이트</h4>
                      <ul className="text-sm text-blue-700 space-y-1">
                        <li>• 4개의 구별되는 페르소나로 세분화된 사용자 그룹 분석 가능</li>
                        <li>• 데이터 커버리지 40% 향상으로 더 포괄적인 분석 가능</li>
                        <li>• 실제 사용자 패턴과 89% 일치율로 높은 현실성 달성</li>
                        <li>• 개인화 서비스 개발을 위한 구체적인 니즈 파악</li>
                      </ul>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}