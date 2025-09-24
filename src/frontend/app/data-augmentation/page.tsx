'use client'

import React, { useState, useCallback } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  ArrowLeft,
  Upload,
  FileSpreadsheet,
  FileText,
  Database,
  Brain,
  Zap,
  CheckCircle,
  Clock,
  AlertCircle,
  Download,
  BarChart3,
  Users,
  FileDown
} from 'lucide-react'
import { apiClient, apiUtils, APIError } from '@/lib/api-client'

// 업로드 단계 상태
type UploadStep = 'upload' | 'analyzing' | 'generating' | 'augmenting' | 'completed'

interface UploadedFile {
  name: string
  size: number
  type: string
  uploadedAt: Date
}

interface AnalysisTask {
  taskId: string
  status: UploadStep
  progress: number
  structuredFile?: UploadedFile
  knowledgeFiles: UploadedFile[]
  structuredFilePath?: string
  knowledgeFilePaths: string[]
  results?: {
    clustersFound: number
    personasGenerated: number
    dataAugmented: number
    performanceImprovement: number
  }
  error?: string
}

export default function DataAugmentationPage() {
  const [currentTask, setCurrentTask] = useState<AnalysisTask | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [structuredFile, setStructuredFile] = useState<File | null>(null)
  const [knowledgeFiles, setKnowledgeFiles] = useState<File[]>([])

  // 드래그 앤 드롭 핸들러
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent, fileType: 'structured' | 'knowledge') => {
    e.preventDefault()
    setIsDragOver(false)

    const files = Array.from(e.dataTransfer.files)

    if (fileType === 'structured') {
      const csvExcelFiles = files.filter(f =>
        f.name.endsWith('.csv') || f.name.endsWith('.xlsx') || f.name.endsWith('.xls')
      )
      if (csvExcelFiles.length > 0) {
        setStructuredFile(csvExcelFiles[0])
      }
    } else {
      const textFiles = files.filter(f =>
        f.name.endsWith('.pdf') || f.name.endsWith('.txt') || f.name.endsWith('.md')
      )
      setKnowledgeFiles(prev => [...prev, ...textFiles])
    }
  }, [])

  // 파일 선택 핸들러
  const handleFileSelect = (files: FileList | null, fileType: 'structured' | 'knowledge') => {
    if (!files) return

    const fileArray = Array.from(files)

    if (fileType === 'structured') {
      setStructuredFile(fileArray[0])
    } else {
      setKnowledgeFiles(prev => [...prev, ...fileArray])
    }
  }

  // 파일 제거
  const removeStructuredFile = () => setStructuredFile(null)
  const removeKnowledgeFile = (index: number) => {
    setKnowledgeFiles(prev => prev.filter((_, i) => i !== index))
  }

  // 분석 시작
  const startAnalysis = async () => {
    if (!structuredFile || knowledgeFiles.length === 0) {
      alert('정형 데이터와 도메인 지식 파일을 모두 업로드해주세요.')
      return
    }

    try {
      // 1. 정형 데이터 업로드
      const structuredResponse = await apiClient.uploadStructuredData(structuredFile)
      if (!structuredResponse.success) {
        throw new Error('정형 데이터 업로드 실패')
      }

      // 2. 지식 파일들 업로드
      const knowledgeResponse = await apiClient.uploadKnowledgeFiles(knowledgeFiles)
      if (!knowledgeResponse.success) {
        throw new Error('지식 파일 업로드 실패')
      }

      // 3. 분석 시작
      const analysisResponse = await apiClient.startDataAugmentationAnalysis(
        structuredResponse.file_path,
        knowledgeResponse.files.map(f => f.file_path)
      )

      if (!analysisResponse.success) {
        throw new Error('분석 시작 실패')
      }

      // 작업 생성
      const task: AnalysisTask = {
        taskId: analysisResponse.task_id,
        status: 'analyzing',
        progress: 10,
        structuredFile: {
          name: structuredFile.name,
          size: structuredFile.size,
          type: structuredFile.type,
          uploadedAt: new Date()
        },
        knowledgeFiles: knowledgeFiles.map(f => ({
          name: f.name,
          size: f.size,
          type: f.type,
          uploadedAt: new Date()
        })),
        structuredFilePath: structuredResponse.file_path,
        knowledgeFilePaths: knowledgeResponse.files.map(f => f.file_path)
      }

      setCurrentTask(task)

      // 실제 진행 상황 모니터링 시작
      monitorTaskProgress(task.taskId)

    } catch (error) {
      console.error('분석 시작 실패:', error)
      alert(apiUtils.getErrorMessage(error))
    }
  }

  // 실제 작업 진행 상황 모니터링
  const monitorTaskProgress = async (taskId: string) => {
    const pollInterval = 2000 // 2초마다 확인

    const poll = async () => {
      try {
        const statusResponse = await apiClient.getDataAugmentationStatus(taskId)

        setCurrentTask(prev => {
          if (!prev) return null

          const newStatus = mapBackendStatusToFrontend(statusResponse.status)
          return {
            ...prev,
            status: newStatus,
            progress: statusResponse.progress,
            error: statusResponse.error
          }
        })

        // 완료된 경우 결과 가져오기
        if (statusResponse.status === 'completed' && statusResponse.results) {
          setCurrentTask(prev => prev ? {
            ...prev,
            results: {
              clustersFound: statusResponse.results.clusters_found || 0,
              personasGenerated: statusResponse.results.personas_generated || 0,
              dataAugmented: statusResponse.results.data_augmented || 0,
              performanceImprovement: statusResponse.results.performance_improvement || 0
            }
          } : null)
        }

        // 진행 중이면 계속 폴링
        if (statusResponse.status !== 'completed' && statusResponse.status !== 'error') {
          setTimeout(poll, pollInterval)
        }

      } catch (error) {
        console.error('상태 조회 실패:', error)
        setCurrentTask(prev => prev ? {
          ...prev,
          status: 'completed', // 오류 상태 처리
          error: apiUtils.getErrorMessage(error)
        } : null)
      }
    }

    // 첫 폴링 시작
    setTimeout(poll, pollInterval)
  }

  // 백엔드 상태를 프론트엔드 상태로 매핑
  const mapBackendStatusToFrontend = (backendStatus: string): UploadStep => {
    switch (backendStatus) {
      case 'analyzing':
      case 'analysis_complete':
        return 'analyzing'
      case 'processing_knowledge':
      case 'generating_personas':
        return 'generating'
      case 'augmenting':
        return 'augmenting'
      case 'completed':
        return 'completed'
      case 'error':
        return 'completed' // 에러도 완료로 표시
      default:
        return 'analyzing'
    }
  }

  // 새 분석 시작
  const startNewAnalysis = () => {
    setCurrentTask(null)
    setStructuredFile(null)
    setKnowledgeFiles([])
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getStepIcon = (step: UploadStep) => {
    switch (step) {
      case 'analyzing': return <Database className="w-5 h-5 text-blue-600" />
      case 'generating': return <Brain className="w-5 h-5 text-purple-600" />
      case 'augmenting': return <Zap className="w-5 h-5 text-green-600" />
      case 'completed': return <CheckCircle className="w-5 h-5 text-green-600" />
      default: return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  const getStepText = (step: UploadStep) => {
    switch (step) {
      case 'analyzing': return '데이터 분석 및 클러스터링'
      case 'generating': return 'AI 페르소나 생성'
      case 'augmenting': return '데이터 증강 및 성능 평가'
      case 'completed': return '분석 완료'
      default: return '대기 중'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* 헤더 */}
      <div className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  홈으로
                </Button>
              </Link>
              <h1 className="text-xl font-bold text-gray-800">범용 데이터 증강 스튜디오</h1>
            </div>

            <Badge variant="outline" className="px-3 py-1">
              AI 페르소나 생성 엔진
            </Badge>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* 소개 섹션 */}
        <Card className="mb-8">
          <CardHeader className="text-center">
            <CardTitle className="flex items-center justify-center gap-2 text-2xl">
              <Zap className="w-6 h-6 text-yellow-600" />
              어떤 데이터든 AI 페르소나로 재탄생
            </CardTitle>
            <CardDescription className="text-lg">
              정형 데이터와 도메인 지식을 업로드하면, AI가 자동으로 분석하여 의미 있는 페르소나를 생성하고 데이터를 증강합니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-4 text-center">
              <div className="p-4 bg-blue-50 rounded-lg">
                <Database className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                <h3 className="font-semibold">데이터 분석</h3>
                <p className="text-sm text-gray-600">자동 클러스터링 및 패턴 탐지</p>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg">
                <Brain className="w-8 h-8 text-purple-600 mx-auto mb-2" />
                <h3 className="font-semibold">지식 융합</h3>
                <p className="text-sm text-gray-600">도메인 지식과 데이터 결합</p>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <Users className="w-8 h-8 text-green-600 mx-auto mb-2" />
                <h3 className="font-semibold">페르소나 생성</h3>
                <p className="text-sm text-gray-600">현실적인 가상 인물 창조</p>
              </div>
              <div className="p-4 bg-orange-50 rounded-lg">
                <BarChart3 className="w-8 h-8 text-orange-600 mx-auto mb-2" />
                <h3 className="font-semibold">데이터 증강</h3>
                <p className="text-sm text-gray-600">품질 향상된 합성 데이터</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {!currentTask ? (
          // 파일 업로드 단계
          <div className="space-y-8">
            {/* 정형 데이터 업로드 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-green-600" />
                  1. 정형 데이터 업로드
                </CardTitle>
                <CardDescription>
                  분석할 주요 데이터를 업로드하세요. (CSV, Excel 지원)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, 'structured')}
                >
                  {structuredFile ? (
                    <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <FileSpreadsheet className="w-8 h-8 text-green-600" />
                        <div>
                          <p className="font-medium">{structuredFile.name}</p>
                          <p className="text-sm text-gray-600">{formatFileSize(structuredFile.size)}</p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm" onClick={removeStructuredFile}>
                        제거
                      </Button>
                    </div>
                  ) : (
                    <div>
                      <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-lg font-medium text-gray-700 mb-2">
                        정형 데이터 파일을 드래그하거나 클릭하여 업로드
                      </p>
                      <p className="text-gray-600 mb-4">지원 형식: CSV, Excel (.xlsx, .xls)</p>
                      <Label htmlFor="structured-upload">
                        <Button variant="outline" className="cursor-pointer">
                          파일 선택
                        </Button>
                      </Label>
                      <Input
                        id="structured-upload"
                        type="file"
                        accept=".csv,.xlsx,.xls"
                        className="hidden"
                        onChange={(e) => handleFileSelect(e.target.files, 'structured')}
                      />
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 도메인 지식 업로드 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-purple-600" />
                  2. 도메인 지식 업로드
                </CardTitle>
                <CardDescription>
                  데이터와 관련된 도메인 지식 문서를 업로드하세요. (PDF, 텍스트 지원)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center mb-4 transition-colors ${
                    isDragOver ? 'border-purple-500 bg-purple-50' : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, 'knowledge')}
                >
                  <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-lg font-medium text-gray-700 mb-2">
                    도메인 지식 파일을 드래그하거나 클릭하여 업로드
                  </p>
                  <p className="text-gray-600 mb-4">지원 형식: PDF, TXT, MD</p>
                  <Label htmlFor="knowledge-upload">
                    <Button variant="outline" className="cursor-pointer">
                      파일 선택
                    </Button>
                  </Label>
                  <Input
                    id="knowledge-upload"
                    type="file"
                    accept=".pdf,.txt,.md"
                    multiple
                    className="hidden"
                    onChange={(e) => handleFileSelect(e.target.files, 'knowledge')}
                  />
                </div>

                {/* 업로드된 지식 파일들 */}
                {knowledgeFiles.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-gray-700">
                      업로드된 지식 파일 ({knowledgeFiles.length}개)
                    </Label>
                    {knowledgeFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <FileText className="w-6 h-6 text-purple-600" />
                          <div>
                            <p className="font-medium">{file.name}</p>
                            <p className="text-sm text-gray-600">{formatFileSize(file.size)}</p>
                          </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => removeKnowledgeFile(index)}>
                          제거
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 분석 시작 버튼 */}
            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <Button
                    onClick={startAnalysis}
                    disabled={!structuredFile || knowledgeFiles.length === 0}
                    size="lg"
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  >
                    <Zap className="w-5 h-5 mr-2" />
                    AI 페르소나 생성 및 데이터 증강 시작
                  </Button>
                  {(!structuredFile || knowledgeFiles.length === 0) && (
                    <p className="text-sm text-gray-500 mt-2">
                      정형 데이터와 도메인 지식 파일을 모두 업로드해주세요
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          // 분석 진행 및 결과 표시
          <AnalysisProgress task={currentTask} onNewAnalysis={startNewAnalysis} />
        )}
      </div>
    </div>
  )
}

// 분석 진행 상황 컴포넌트
function AnalysisProgress({
  task,
  onNewAnalysis
}: {
  task: AnalysisTask
  onNewAnalysis: () => void
}) {
  return (
    <div className="space-y-8">
      {/* 진행 상황 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getStepIcon(task.status)}
            {getStepText(task.status)}
          </CardTitle>
          <CardDescription>
            전체 진행률: {Math.round(task.progress)}%
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="w-full bg-gray-200 rounded-full h-3 mb-6">
            <div
              className="bg-gradient-to-r from-blue-600 to-purple-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${task.progress}%` }}
            />
          </div>

          <div className="grid md:grid-cols-4 gap-4">
            {(['analyzing', 'generating', 'augmenting', 'completed'] as UploadStep[]).map((step, index) => (
              <div
                key={step}
                className={`p-4 rounded-lg border-2 transition-all ${
                  task.status === step
                    ? 'border-blue-500 bg-blue-50'
                    : task.progress > (index / 4) * 100
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-200 bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  {getStepIcon(step)}
                  <span className="font-medium text-sm">{getStepText(step)}</span>
                </div>
                {task.status === step && task.status !== 'completed' && (
                  <div className="animate-pulse text-xs text-gray-600">처리 중...</div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 업로드된 파일 정보 */}
      <Card>
        <CardHeader>
          <CardTitle>분석 대상 파일</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
              <FileSpreadsheet className="w-6 h-6 text-green-600" />
              <div>
                <p className="font-medium">정형 데이터: {task.structuredFile?.name}</p>
                <p className="text-sm text-gray-600">
                  크기: {task.structuredFile && formatFileSize(task.structuredFile.size)}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-gray-700">
                도메인 지식 ({task.knowledgeFiles.length}개 파일)
              </Label>
              {task.knowledgeFiles.map((file, index) => (
                <div key={index} className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
                  <FileText className="w-6 h-6 text-purple-600" />
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-gray-600">크기: {formatFileSize(file.size)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 결과 표시 (완료된 경우) */}
      {task.status === 'completed' && task.results && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-6 h-6 text-green-600" />
              분석 완료 및 결과
            </CardTitle>
            <CardDescription>
              AI 페르소나 생성 및 데이터 증강이 성공적으로 완료되었습니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600 mb-1">
                  {task.results.clustersFound}
                </div>
                <div className="text-sm text-gray-600">발견된 클러스터</div>
              </div>

              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600 mb-1">
                  {task.results.personasGenerated}
                </div>
                <div className="text-sm text-gray-600">생성된 페르소나</div>
              </div>

              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600 mb-1">
                  {task.results.dataAugmented.toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">증강된 데이터 행</div>
              </div>

              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600 mb-1">
                  +{task.results.performanceImprovement}%
                </div>
                <div className="text-sm text-gray-600">성능 개선</div>
              </div>
            </div>

            <div className="flex gap-4 justify-center">
              <Button variant="outline" className="flex items-center gap-2">
                <Download className="w-4 h-4" />
                증강된 데이터 다운로드
              </Button>

              <Button variant="outline" className="flex items-center gap-2">
                <FileDown className="w-4 h-4" />
                페르소나 리포트 다운로드
              </Button>

              <Button
                onClick={onNewAnalysis}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              >
                새로운 분석 시작
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function getStepIcon(step: UploadStep) {
  switch (step) {
    case 'analyzing': return <Database className="w-5 h-5 text-blue-600" />
    case 'generating': return <Brain className="w-5 h-5 text-purple-600" />
    case 'augmenting': return <Zap className="w-5 h-5 text-green-600" />
    case 'completed': return <CheckCircle className="w-5 h-5 text-green-600" />
    default: return <Clock className="w-5 h-5 text-gray-400" />
  }
}

function getStepText(step: UploadStep) {
  switch (step) {
    case 'analyzing': return '데이터 분석 및 클러스터링'
    case 'generating': return 'AI 페르소나 생성'
    case 'augmenting': return '데이터 증강 및 성능 평가'
    case 'completed': return '분석 완료'
    default: return '대기 중'
  }
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}