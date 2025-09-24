'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Upload, FileText, Database, Bot, CheckCircle, XCircle, Loader2, Download } from 'lucide-react'

const API_URL = 'http://54.183.202.72:8000'

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
  const [ws, setWs] = useState<WebSocket | null>(null)

  // WebSocket 연결
  useEffect(() => {
    if (taskId && !ws) {
      const websocket = new WebSocket(`ws://54.183.202.72:8000/ws/${taskId}`)

      websocket.onopen = () => {
        console.log('WebSocket 연결됨')
        setWs(websocket)
      }

      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        console.log('WebSocket 메시지:', data)

        if (data.type === 'progress') {
          setTaskStatus(prev => ({
            ...prev,
            task_id: taskId,
            status: 'running',
            progress: data.progress,
            current_stage: data.stage,
            message: data.message
          }))
        } else if (data.type === 'completed') {
          setTaskStatus(prev => ({
            ...prev,
            task_id: taskId,
            status: 'completed',
            progress: 100,
            current_stage: '완료',
            results: data.results
          }))
          setIsProcessing(false)
        } else if (data.type === 'error') {
          setTaskStatus(prev => ({
            ...prev,
            task_id: taskId,
            status: 'failed',
            error: data.error
          }))
          setIsProcessing(false)
        }
      }

      websocket.onerror = (error) => {
        console.error('WebSocket 오류:', error)
      }

      websocket.onclose = () => {
        console.log('WebSocket 연결 종료')
        setWs(null)
      }

      return () => {
        websocket.close()
      }
    }
  }, [taskId, ws])

  // 정형 데이터 파일 업로드
  const handleStructuredFileUpload = async () => {
    if (!structuredFile) return

    setIsUploading(true)
    setUploadStatus('정형 데이터 업로드 중...')

    try {
      const formData = new FormData()
      formData.append('file', structuredFile)

      const response = await fetch(`${API_URL}/api/v1/upload/structured-data`, {
        method: 'POST',
        body: formData
      })

      const result: UploadResponse = await response.json()

      if (result.success) {
        setStructuredFileId(result.file_path || '')
        setUploadStatus('정형 데이터 업로드 완료!')
      } else {
        setUploadStatus('업로드 실패: ' + result.message)
      }
    } catch (error) {
      setUploadStatus('업로드 오류: ' + (error instanceof Error ? error.message : '알 수 없는 오류'))
    }

    setIsUploading(false)
  }

  // 지식 파일들 업로드
  const handleKnowledgeFilesUpload = async () => {
    if (knowledgeFiles.length === 0) return

    setIsUploading(true)
    setUploadStatus('지식 파일들 업로드 중...')

    try {
      const formData = new FormData()
      knowledgeFiles.forEach(file => {
        formData.append('files', file)
      })

      const response = await fetch(`${API_URL}/api/v1/upload/knowledge-files`, {
        method: 'POST',
        body: formData
      })

      const result: UploadResponse = await response.json()

      if (result.success) {
        const paths = result.files?.map(f => f.file_path) || []
        setKnowledgeFilePaths(paths)
        setUploadStatus('지식 파일들 업로드 완료!')
      } else {
        setUploadStatus('업로드 실패: ' + result.message)
      }
    } catch (error) {
      setUploadStatus('업로드 오류: ' + (error instanceof Error ? error.message : '알 수 없는 오류'))
    }

    setIsUploading(false)
  }

  // 데이터 증강 시작
  const startAugmentation = async () => {
    if (!structuredFileId || knowledgeFilePaths.length === 0) {
      alert('파일을 먼저 업로드해주세요.')
      return
    }

    setIsProcessing(true)

    try {
      const requestBody = {
        knowledge_file_paths: knowledgeFilePaths,
        config: {
          scenario: "normal",
          domain: "general",
          target_samples: 1000,
          augmentation_strategies: ["interpolation", "noise_addition", "pattern_variation"],
          target_columns: []
        }
      }

      // structured_file_path를 query parameter로 추가
      const url = `${API_URL}/api/v1/augmentation/start?structured_file_path=${encodeURIComponent(structuredFileId)}`

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      })

      const result = await response.json()

      if (result.success) {
        setTaskId(result.task_id)
        setTaskStatus({
          task_id: result.task_id,
          status: result.status,
          progress: 0,
          current_stage: '시작됨'
        })
      } else {
        alert('작업 시작 실패: ' + result.message)
        setIsProcessing(false)
      }
    } catch (error) {
      alert('작업 시작 오류: ' + (error instanceof Error ? error.message : '알 수 없는 오류'))
      setIsProcessing(false)
    }
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
              <div className="space-y-4">
                <div className="p-4 bg-green-50 border border-green-200 rounded">
                  <p className="text-green-600 font-medium">데이터 증강이 완료되었습니다!</p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Button
                    variant="outline"
                    onClick={() => downloadResults('personas')}
                    className="flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    페르소나
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => downloadResults('augmented_data')}
                    className="flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    증강 데이터
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
                    평가 결과
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}