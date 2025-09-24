'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  ArrowLeft,
  Users,
  RefreshCw,
  Activity,
  User,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  Brain,
  Database
} from 'lucide-react'
import {
  apiClient,
  apiUtils,
  APIError,
  PersonaGenerateResponse,
  PersonaListResponse,
  SystemMetrics
} from '@/lib/api-client'

interface Persona {
  persona_id: string
  name: string
  age: number
  gender: string
  cluster_id: number
  living_situation: string
  welfare_needs: string[]
  risk_factors: string[]
  behavioral_patterns: Record<string, any>
  rag_insights: string[]
}

export default function PersonasPage() {
  const [personas, setPersonas] = useState<Persona[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null)
  const [lastGenerated, setLastGenerated] = useState<string | null>(null)

  // 페이지 로드 시 기존 페르소나 및 시스템 상태 확인
  useEffect(() => {
    loadPersonas()
    loadSystemMetrics()
  }, [])

  // 페르소나 목록 로드
  const loadPersonas = async () => {
    setIsLoading(true)
    setConnectionError(null)

    try {
      const response = await apiClient.getPersonas()
      setPersonas(response.personas)
      if (response.cache_timestamp) {
        setLastGenerated(response.cache_timestamp)
      }
    } catch (error) {
      console.error('페르소나 로딩 실패:', error)
      setConnectionError(apiUtils.getErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }

  // 시스템 메트릭 로드
  const loadSystemMetrics = async () => {
    try {
      const metrics = await apiClient.getSystemMetrics()
      setSystemMetrics(metrics)
    } catch (error) {
      console.error('시스템 메트릭 로딩 실패:', error)
    }
  }

  // 새 페르소나 생성
  const generatePersonas = async () => {
    setIsGenerating(true)
    setConnectionError(null)

    try {
      const response = await apiClient.generatePersonas({
        n_personas: 5,
        force_regenerate: true,
        use_clustering: true
      })

      if (response.personas) {
        // 즉시 생성된 경우
        setPersonas(response.personas)
        setLastGenerated(new Date().toISOString())
      } else {
        // 백그라운드 생성의 경우 일정 시간 후 다시 로드
        setTimeout(() => {
          loadPersonas()
        }, 3000)
      }
    } catch (error) {
      console.error('페르소나 생성 실패:', error)
      setConnectionError(apiUtils.getErrorMessage(error))
    } finally {
      setIsGenerating(false)
    }
  }

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '없음'
    return new Date(isoString).toLocaleString('ko-KR')
  }

  const getGenderIcon = (gender: string) => {
    return gender === 'male' ? '👨' : '👩'
  }

  const getRiskBadgeVariant = (riskFactors: string[]) => {
    if (riskFactors.length >= 3) return 'destructive'
    if (riskFactors.length >= 1) return 'secondary'
    return 'outline'
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
              <h1 className="text-xl font-bold text-gray-800">AI 페르소나 관리</h1>
            </div>

            <div className="flex items-center gap-2">
              <Button
                onClick={loadSystemMetrics}
                variant="outline"
                size="sm"
              >
                <Activity className="w-4 h-4" />
              </Button>
              <Button
                onClick={loadPersonas}
                variant="outline"
                size="sm"
                disabled={isLoading}
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* 시스템 상태 카드 */}
        {systemMetrics && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="w-5 h-5 text-blue-600" />
                시스템 상태
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Brain className="w-5 h-5 text-green-600" />
                    <span className="text-sm font-medium">AWS Bedrock</span>
                  </div>
                  <Badge variant={systemMetrics.aws.bedrock_available ? "default" : "destructive"}>
                    {systemMetrics.aws.bedrock_available ? '사용 가능' : '사용 불가'}
                  </Badge>
                </div>

                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Users className="w-5 h-5 text-blue-600" />
                    <span className="text-sm font-medium">클러스터링</span>
                  </div>
                  <Badge variant={systemMetrics.data_modules.clustering_available ? "default" : "destructive"}>
                    {systemMetrics.data_modules.clustering_available ? '사용 가능' : '사용 불가'}
                  </Badge>
                </div>

                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Database className="w-5 h-5 text-purple-600" />
                    <span className="text-sm font-medium">RAG 지식베이스</span>
                  </div>
                  <Badge variant={systemMetrics.data_modules.rag_available ? "default" : "destructive"}>
                    {systemMetrics.data_modules.rag_available ? '사용 가능' : '사용 불가'}
                  </Badge>
                </div>

                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Activity className="w-5 h-5 text-orange-600" />
                    <span className="text-sm font-medium">캐시 상태</span>
                  </div>
                  <Badge variant={systemMetrics.cache.personas_cached ? "default" : "secondary"}>
                    {systemMetrics.cache.personas_cached ? '캐시됨' : '없음'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 연결 오류 표시 */}
        {connectionError && (
          <Card className="mb-8 border-red-200 bg-red-50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-6 h-6 text-red-600" />
                <div>
                  <h3 className="font-semibold text-red-800">서버 연결 오류</h3>
                  <p className="text-red-700">{connectionError}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 페르소나 생성 컨트롤 */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>페르소나 생성</CardTitle>
            <CardDescription>
              AWS Bedrock Claude 모델을 사용하여 서울시 1인가구 데이터 기반 AI 페르소나를 생성합니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                마지막 생성: {formatDateTime(lastGenerated)}
              </div>
              <Button
                onClick={generatePersonas}
                disabled={isGenerating || isLoading}
                className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    생성 중...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 mr-2" />
                    새 페르소나 생성
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 페르소나 목록 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-600" />
              생성된 페르소나 목록 ({personas.length}개)
            </CardTitle>
            <CardDescription>
              클러스터링 분석과 RAG 지식 증강을 통해 생성된 AI 페르소나들입니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
                <p className="text-gray-600">페르소나 데이터를 불러오는 중...</p>
              </div>
            ) : personas.length === 0 ? (
              <div className="text-center py-8">
                <Users className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p className="text-gray-600 mb-4">생성된 페르소나가 없습니다.</p>
                <Button onClick={generatePersonas} variant="outline">
                  첫 페르소나 생성하기
                </Button>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {personas.map((persona) => (
                  <Card key={persona.persona_id} className="hover:shadow-lg transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="text-2xl">
                          {getGenderIcon(persona.gender)}
                        </div>
                        <div>
                          <CardTitle className="text-lg">{persona.name}</CardTitle>
                          <p className="text-sm text-gray-600">
                            {persona.age}세 {persona.gender === 'male' ? '남성' : '여성'}
                          </p>
                        </div>
                        <Badge variant="outline" className="ml-auto">
                          클러스터 {persona.cluster_id}
                        </Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-4">
                      {/* 생활 상황 */}
                      <div>
                        <h4 className="font-medium text-sm text-gray-700 mb-2">생활 상황</h4>
                        <p className="text-sm text-gray-600 line-clamp-2">
                          {persona.living_situation}
                        </p>
                      </div>

                      {/* 복지 욕구 */}
                      <div>
                        <h4 className="font-medium text-sm text-gray-700 mb-2">복지 욕구</h4>
                        <div className="flex flex-wrap gap-1">
                          {persona.welfare_needs.slice(0, 3).map((need, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              {need}
                            </Badge>
                          ))}
                          {persona.welfare_needs.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{persona.welfare_needs.length - 3}
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* 위험 요소 */}
                      <div>
                        <h4 className="font-medium text-sm text-gray-700 mb-2">위험 요소</h4>
                        <div className="flex flex-wrap gap-1">
                          {persona.risk_factors.length > 0 ? (
                            persona.risk_factors.slice(0, 2).map((risk, idx) => (
                              <Badge
                                key={idx}
                                variant={getRiskBadgeVariant(persona.risk_factors)}
                                className="text-xs"
                              >
                                {risk}
                              </Badge>
                            ))
                          ) : (
                            <Badge variant="outline" className="text-xs">
                              위험 요소 없음
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* RAG 인사이트 */}
                      {persona.rag_insights.length > 0 && (
                        <div>
                          <h4 className="font-medium text-sm text-gray-700 mb-2 flex items-center gap-1">
                            <Brain className="w-3 h-3" />
                            AI 인사이트
                          </h4>
                          <p className="text-xs text-gray-600 line-clamp-2">
                            {persona.rag_insights[0]}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}