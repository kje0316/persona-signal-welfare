"use client"

import React, { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Send, MessageCircle, User, AlertTriangle, CheckCircle, Clock, Heart, Zap } from 'lucide-react'

interface Message {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
}

interface PreConsultationData {
  gender: string
  age: string
  region: string
  income: string
  targetGroup: string
  household: string
  housing: string
  timestamp: string
}

interface WelfareService {
  service_id: string
  service_name: string
  service_type: string
  service_summary: string
  detailed_link: string
  managing_agency: string
  region_sido: string
  region_sigungu: string
  department: string
  contact_phone: string
  contact_email: string
  address: string
  support_target: string
  selection_criteria: string
  support_content: string
  support_cycle: string
  payment_method: string
  application_method: string
  required_documents: string
  category: string
  life_cycle: string
  target_characteristics: string
  interest_topics: string
  service_status: string
  start_date: string
  end_date: string
  view_count: number
  last_updated: string
  created_at: string
  updated_at: string
}

// 위험도 평가 레벨
type RiskLevel = 'safe' | 'caution' | 'danger'

interface RiskAssessment {
  level: RiskLevel
  score: number
  factors: string[]
  recommendations: string[]
}

export default function ConsultationPage() {
  const [preData, setPreData] = useState<PreConsultationData | null>(null)
  const [currentPhase, setCurrentPhase] = useState<'preview' | 'chat' | 'results'>('preview')
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [recommendedServices, setRecommendedServices] = useState<WelfareService[]>([])
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null)
  const [chatTurnCount, setChatTurnCount] = useState(0)
  const [isLoadingServices, setIsLoadingServices] = useState(false)
  const [servicesError, setServicesError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 컴포넌트 마운트 시 세션 데이터 로드
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedData = sessionStorage.getItem('preConsultationData')
      if (storedData) {
        const data = JSON.parse(storedData)
        setPreData(data)

        // 초기 AI 메시지 생성
        const initialMessage = generateInitialMessage(data)
        setMessages([{
          id: '1',
          content: initialMessage,
          sender: 'ai',
          timestamp: new Date()
        }])
      }
    }
  }, [])

  // 스크롤 자동 이동
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 1차 필터링 결과 로드
  useEffect(() => {
    if (preData) {
      loadRecommendedServices(preData)
    }
  }, [preData])

  // 초기 AI 메시지 생성
  const generateInitialMessage = (data: PreConsultationData): string => {
    const genderText = data.gender === 'male' ? '남성' : '여성'

    const ageText = {
      'child': '아동·청소년 (18세 이하)',
      'youth': '청년 (19-39세)',
      'middle': '중장년 (40-64세)',
      'senior': '노인 (65세 이상)',
      'all': '연령 무관'
    }[data.age] || data.age

    const regionText = {
      'seoul': '서울특별시',
      'busan': '부산광역시',
      'daegu': '대구광역시',
      'incheon': '인천광역시',
      'gwangju': '광주광역시',
      'daejeon': '대전광역시',
      'ulsan': '울산광역시',
      'sejong': '세종특별자치시',
      'gyeonggi': '경기도',
      'gangwon': '강원도',
      'chungbuk': '충청북도',
      'chungnam': '충청남도',
      'jeonbuk': '전라북도',
      'jeonnam': '전라남도',
      'gyeongbuk': '경상북도',
      'gyeongnam': '경상남도',
      'jeju': '제주특별자치도'
    }[data.region] || data.region

    const targetGroupText = {
      'general': '일반',
      'single_parent': '한부모 가정',
      'disability': '장애인',
      'veteran': '국가유공자',
      'multi_child': '다자녀 가정',
      'multicultural': '다문화 가정'
    }[data.targetGroup] || data.targetGroup

    const householdText = {
      'single': '1인 가구',
      'couple': '2인 가구',
      'family_3': '3인 가구',
      'family_4_plus': '4인 이상 가구'
    }[data.household] || data.household

    const housingText = {
      'homeless': '무주택자',
      'monthly_rent': '월세 거주',
      'jeonse': '전세 거주',
      'rental': '임대주택 거주',
      'owned': '자가 소유',
      'all': '주거형태 무관',
      'unknown': '기타'
    }[data.housing] || data.housing

    return `안녕하세요! 복지 전문 상담사 AI입니다. 😊

먼저 입력해주신 기본 정보를 정리해보았습니다:
👤 ${genderText} · 🎂 ${ageText} · 📍 ${regionText}
💰 ${getIncomeText(data.income)} · 👥 ${targetGroupText}
🏠 ${householdText} · 🏡 ${housingText}

기본 조건으로 찾은 복지 서비스들이 있지만, 더욱 정확하고 도움이 되는 추천을 드리고 싶습니다.

현재 상황을 자세히 말씀해 주세요:
✅ 지금 가장 어려운 점이나 긴급한 도움이 필요한 부분
✅ 함께 사는 가족이나 돌봐야 할 분이 있는지
✅ 건강, 일자리, 주거 등 특별한 상황
✅ 이전에 받아본 복지 혜택이나 신청 경험

어떤 내용이든 편하게 말씀해 주세요. 차근차근 도와드리겠습니다! 💪`
  }

  // 소득 텍스트 변환
  const getIncomeText = (income: string): string => {
    const incomeMap = {
      'low': '150만원 이하',
      'middle-low': '150-300만원',
      'middle': '300-500만원',
      'high': '500만원 이상'
    }
    return incomeMap[income as keyof typeof incomeMap] || income
  }

  // 1차 필터링 서비스 로드 - 백엔드 API 사용
  const loadRecommendedServices = async (data: PreConsultationData) => {
    setIsLoadingServices(true)
    setServicesError(null)

    try {
      // 백엔드 API 엔드포인트 구성
      const queryParams = new URLSearchParams({
        gender: data.gender,
        age: data.age,
        region: data.region,
        income: data.income,
        targetGroup: data.targetGroup,
        household: data.household,
        housing: data.housing,
        limit: '20', // 더 많은 서비스 가져오기
        offset: '0'
      })

      const response = await fetch(`http://54.183.202.72:8001/welfare-services?${queryParams.toString()}`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      console.log('백엔드에서 가져온 복지 서비스:', result.total, '개')

      setRecommendedServices(result.services || [])

      if (result.total === 0) {
        setServicesError('입력하신 조건에 정확히 일치하는 서비스를 찾을 수 없습니다. AI 상담을 통해 더 넓은 범위의 서비스를 추천받아보세요.')
      }
    } catch (error) {
      console.error('백엔드 API 오류:', error)
      setServicesError('복지 서비스 데이터를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
      setRecommendedServices([])
    } finally {
      setIsLoadingServices(false)
    }
  }

  // 메시지 전송 - 실제 백엔드 API 사용
  const sendMessage = async () => {
    if (!inputMessage.trim() || !preData) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      // 백엔드 챗봇 API 호출
      const chatHistory = messages.map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: msg.timestamp
      }))

      const response = await fetch('http://54.183.202.72:8001/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: inputMessage,
          user_profile: preData,
          conversation_history: chatHistory
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: result.response,
        sender: 'ai',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, aiMessage])

      // 채팅 턴 카운트 증가
      setChatTurnCount(prev => prev + 1)

      // 5턴 이상 진행시 결과 단계로 전환
      if (chatTurnCount >= 4) {
        setTimeout(() => {
          const risk = assessRisk(messages.concat([userMessage]))
          setRiskAssessment(risk)
          setCurrentPhase('results')
        }, 2000)
      }

    } catch (error) {
      console.error('챗봇 API 오류:', error)

      // 오류 발생 시 폴백 응답
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `죄송합니다. 일시적으로 상담 서비스에 문제가 발생했습니다.

다음 방법으로 도움받으실 수 있습니다:
📞 다산콜센터: 120 (무료)
🏢 거주지 주민센터 방문 상담
🌐 복지로 온라인: www.bokjiro.go.kr

잠시 후 다시 시도해주세요.`,
        sender: 'ai',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  // AI 응답 생성
  const generateAIResponse = (userInput: string, turnCount: number): { content: string, shouldFinish: boolean } => {
    const input = userInput.toLowerCase()

    // 위험 신호 감지
    const emergencyKeywords = ['자살', '죽고싶', '안전하지', '폭력', '위험', '응급', '급해', '힘들어서', '견딜수없']
    const isEmergency = emergencyKeywords.some(keyword => input.includes(keyword))

    if (isEmergency) {
      return {
        content: `⚠️ 지금 상황이 매우 어려우시군요. 즉시 도움을 받으실 수 있습니다.

**긴급 연락처:**
- 생명의 전화: 1393 (24시간)
- 청소년 전화: 1388
- 다산콜센터: 120

안전한 곳에 계시면서 위 번호로 연락해주세요. 전문 상담사가 도움을 드릴 수 있습니다.

그리고 복지 서비스 측면에서도 긴급지원제도나 위기가구 지원이 가능할 수 있으니, 상황이 안정되면 다시 상담받으시기 바랍니다.`,
        shouldFinish: true
      }
    }

    // 상담 진행 단계별 응답
    if (turnCount === 1) {
      return {
        content: `상황을 이해했습니다. 몇 가지 더 확인하고 싶은 것이 있어요.

현재 같이 살고 계신 가족이 있으신가요? 그리고 지금 상황에서 가장 시급하게 해결되어야 할 문제가 무엇인지 알려주세요.

또한 현재 다른 복지 서비스를 받고 계시거나 신청해본 경험이 있으시면 말씀해 주세요.`,
        shouldFinish: false
      }
    } else if (turnCount === 2) {
      return {
        content: `네, 잘 알겠습니다. 마지막으로 몇 가지만 더 확인할게요.

1. 현재 경제적 상황에서 한 달에 어느 정도의 지원이 있으면 도움이 될까요?
2. 복지 서비스 신청 과정에서 어려움이 있었다면 어떤 부분이었나요?
3. 혹시 주변에서 도움을 받을 수 있는 분이 계신가요?

이 정보를 바탕으로 맞춤형 복지 서비스를 추천해드리겠습니다.`,
        shouldFinish: false
      }
    } else {
      return {
        content: `상세한 정보를 알려주셔서 감사합니다.

말씀해주신 내용을 종합해서 위험도 평가와 함께 맞춤형 복지 서비스를 추천해드리겠습니다.

잠시만 기다려주세요...`,
        shouldFinish: true
      }
    }
  }

  // 위험도 평가
  const assessRisk = (messages: Message[]): RiskAssessment => {
    const allText = messages.filter(m => m.sender === 'user').map(m => m.content).join(' ').toLowerCase()

    let score = 0
    const factors: string[] = []
    const recommendations: string[] = []

    // 경제적 위험 요소
    if (allText.includes('돈이없') || allText.includes('생활비') || allText.includes('빚')) {
      score += 30
      factors.push('경제적 어려움')
      recommendations.push('기초생활보장 신청 검토')
    }

    // 건강 위험 요소
    if (allText.includes('아프') || allText.includes('병원') || allText.includes('치료')) {
      score += 20
      factors.push('건강 문제')
      recommendations.push('의료급여 및 의료비 지원 확인')
    }

    // 사회적 고립
    if (allText.includes('혼자') || allText.includes('외로') || allText.includes('도와줄사람')) {
      score += 25
      factors.push('사회적 고립')
      recommendations.push('지역 복지관 상담 서비스 이용')
    }

    // 주거 불안정
    if (allText.includes('집이없') || allText.includes('월세') || allText.includes('이사')) {
      score += 35
      factors.push('주거 불안정')
      recommendations.push('주거급여 및 임대주택 신청')
    }

    // 기본 추천사항
    recommendations.push('주민센터 방문 상담')
    recommendations.push('복지로(www.bokjiro.go.kr) 온라인 신청')

    let level: RiskLevel = 'safe'
    if (score >= 70) level = 'danger'
    else if (score >= 40) level = 'caution'

    return {
      level,
      score,
      factors: factors.length > 0 ? factors : ['특별한 위험 요소 없음'],
      recommendations
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!preData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="text-center p-8">
            <h2 className="text-xl font-bold mb-4">상담 정보가 없습니다</h2>
            <p className="text-gray-600 mb-4">홈페이지에서 기본 정보를 입력한 후 상담을 시작해주세요.</p>
            <Link href="/">
              <Button>홈으로 돌아가기</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
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
              <h1 className="text-xl font-bold text-gray-800">AI 맞춤 복지 상담</h1>
            </div>

            {/* 진행 상태 표시 */}
            <div className="flex items-center gap-2 text-sm">
              <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                currentPhase === 'preview' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'
              }`}>
                <CheckCircle className="w-4 h-4" />
                1차 필터링
              </div>
              <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                currentPhase === 'chat' ? 'bg-green-100 text-green-700' :
                currentPhase === 'results' ? 'bg-gray-100 text-gray-500' : 'bg-gray-100 text-gray-500'
              }`}>
                <MessageCircle className="w-4 h-4" />
                AI 상담
              </div>
              <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                currentPhase === 'results' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500'
              }`}>
                <Heart className="w-4 h-4" />
                결과 및 추천
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {currentPhase === 'preview' && (
          <PreviewPhase
            preData={preData}
            recommendedServices={recommendedServices}
            onStartChat={() => setCurrentPhase('chat')}
            isLoadingServices={isLoadingServices}
            servicesError={servicesError}
          />
        )}

        {currentPhase === 'chat' && (
          <ChatPhase
            messages={messages}
            inputMessage={inputMessage}
            setInputMessage={setInputMessage}
            isLoading={isLoading}
            onSendMessage={sendMessage}
            onKeyPress={handleKeyPress}
            messagesEndRef={messagesEndRef}
            inputRef={inputRef}
          />
        )}

        {currentPhase === 'results' && riskAssessment && (
          <ResultsPhase
            preData={preData}
            riskAssessment={riskAssessment}
            recommendedServices={recommendedServices}
            chatMessages={messages}
          />
        )}
      </div>
    </div>
  )
}

// 1차 필터링 미리보기 단계
function PreviewPhase({
  preData,
  recommendedServices,
  onStartChat,
  isLoadingServices,
  servicesError
}: {
  preData: PreConsultationData
  recommendedServices: WelfareService[]
  onStartChat: () => void
  isLoadingServices: boolean
  servicesError: string | null
}) {
  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* 선택 정보 요약 */}
      <Card>
        <CardHeader>
          <CardTitle>📋 입력하신 정보</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <div className="text-xs text-gray-600">성별</div>
              <div className="font-semibold text-sm">{preData.gender === 'male' ? '남성' : '여성'}</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <div className="text-xs text-gray-600">연령대</div>
              <div className="font-semibold text-sm">
                {{
                  'child': '아동·청소년',
                  'youth': '청년',
                  'middle': '중장년',
                  'senior': '노인',
                  'all': '연령 무관'
                }[preData.age] || preData.age}
              </div>
            </div>
            <div className="text-center p-3 bg-purple-50 rounded-lg">
              <div className="text-xs text-gray-600">거주지역</div>
              <div className="font-semibold text-sm">
                {{
                  'seoul': '서울',
                  'busan': '부산',
                  'daegu': '대구',
                  'incheon': '인천',
                  'gwangju': '광주',
                  'daejeon': '대전',
                  'ulsan': '울산',
                  'sejong': '세종',
                  'gyeonggi': '경기도',
                  'gangwon': '강원도',
                  'chungbuk': '충북',
                  'chungnam': '충남',
                  'jeonbuk': '전북',
                  'jeonnam': '전남',
                  'gyeongbuk': '경북',
                  'gyeongnam': '경남',
                  'jeju': '제주'
                }[preData.region] || preData.region}
              </div>
            </div>
            <div className="text-center p-3 bg-orange-50 rounded-lg">
              <div className="text-xs text-gray-600">소득 수준</div>
              <div className="font-semibold text-sm">
                {{
                  'basic_recipient': '기초생활수급자',
                  'near_poor': '차상위계층',
                  'median_100': '중위소득 100%↓',
                  'median_150': '중위소득 150%↓',
                  'all': '소득 무관',
                  'unknown': '기타'
                }[preData.income] || preData.income}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 mt-3">
            <div className="text-center p-3 bg-pink-50 rounded-lg">
              <div className="text-xs text-gray-600">대상유형</div>
              <div className="font-semibold text-sm">
                {{
                  'general': '일반',
                  'single_parent': '한부모',
                  'disability': '장애인',
                  'veteran': '국가유공자',
                  'multi_child': '다자녀',
                  'multicultural': '다문화'
                }[preData.targetGroup] || preData.targetGroup}
              </div>
            </div>
            <div className="text-center p-3 bg-cyan-50 rounded-lg">
              <div className="text-xs text-gray-600">가구형태</div>
              <div className="font-semibold text-sm">
                {{
                  'single': '1인',
                  'couple': '2인',
                  'family_3': '3인',
                  'family_4_plus': '4인+'
                }[preData.household] || preData.household}
              </div>
            </div>
            <div className="text-center p-3 bg-yellow-50 rounded-lg">
              <div className="text-xs text-gray-600">주거상황</div>
              <div className="font-semibold text-sm">
                {{
                  'homeless': '무주택',
                  'monthly_rent': '월세',
                  'jeonse': '전세',
                  'rental': '임대',
                  'owned': '자가',
                  'all': '무관',
                  'unknown': '기타'
                }[preData.housing] || preData.housing}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 1차 추천 서비스 */}
      <Card>
        <CardHeader>
          <CardTitle>🎯 1차 추천 복지 서비스</CardTitle>
          <CardDescription>
            입력하신 정보를 바탕으로 {recommendedServices.length}개의 서비스를 찾았습니다.
            AI 상담을 통해 더 정확한 추천을 받아보세요.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingServices ? (
            <div className="flex items-center justify-center p-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-4"></div>
              <span className="text-gray-600">복지 서비스를 검색하고 있습니다...</span>
            </div>
          ) : servicesError ? (
            <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg mb-6">
              <div className="flex items-center mb-2">
                <AlertTriangle className="w-5 h-5 text-yellow-600 mr-2" />
                <span className="font-medium text-yellow-800">알림</span>
              </div>
              <p className="text-yellow-700">{servicesError}</p>
            </div>
          ) : recommendedServices.length > 0 ? (
            <div className="grid md:grid-cols-2 gap-4 mb-6">
              {recommendedServices.slice(0, 4).map((service, index) => (
                <div key={service.service_id} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
                  <h4 className="font-semibold text-gray-800 mb-2">{service.service_name}</h4>
                  <p className="text-sm text-gray-600 mb-2">{service.managing_agency || service.department}</p>
                  <p className="text-sm text-gray-700 line-clamp-2">{service.service_summary}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      {service.service_type === 'government' ? '중앙부처' :
                       service.service_type === 'local' ? '지자체' : '민간'}
                    </span>
                    {service.category && (
                      <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                        {service.category}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          <div className="text-center">
            <Button onClick={onStartChat} size="lg" className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700">
              <MessageCircle className="w-5 h-5 mr-2" />
              AI 상담으로 정확한 추천받기
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// AI 상담 단계
function ChatPhase({
  messages,
  inputMessage,
  setInputMessage,
  isLoading,
  onSendMessage,
  onKeyPress,
  messagesEndRef,
  inputRef
}: {
  messages: Message[]
  inputMessage: string
  setInputMessage: (value: string) => void
  isLoading: boolean
  onSendMessage: () => void
  onKeyPress: (e: React.KeyboardEvent) => void
  messagesEndRef: React.RefObject<HTMLDivElement>
  inputRef: React.RefObject<HTMLInputElement>
}) {
  return (
    <div className="max-w-4xl mx-auto">
      <Card className="h-[600px] flex flex-col">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-blue-600" />
            AI 복지 상담
          </CardTitle>
          <CardDescription>
            상황을 자세히 말씀해주시면 위험도 평가와 함께 맞춤형 서비스를 추천해드립니다.
          </CardDescription>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto p-6">
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] p-4 rounded-lg ${
                  message.sender === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  <div className={`text-xs mt-2 ${
                    message.sender === 'user' ? 'text-blue-100' : 'text-gray-500'
                  }`}>
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 p-4 rounded-lg">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span className="text-gray-600">AI가 답변을 준비하고 있습니다...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </CardContent>

        <div className="border-t p-4">
          <div className="flex gap-3">
            <Input
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={onKeyPress}
              placeholder="상황을 자세히 말씀해주세요..."
              className="flex-1"
              disabled={isLoading}
            />
            <Button onClick={onSendMessage} disabled={isLoading || !inputMessage.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

// 결과 및 추천 단계
function ResultsPhase({
  preData,
  riskAssessment,
  recommendedServices,
  chatMessages
}: {
  preData: PreConsultationData
  riskAssessment: RiskAssessment
  recommendedServices: WelfareService[]
  chatMessages: Message[]
}) {
  const getRiskColor = (level: RiskLevel) => {
    switch (level) {
      case 'safe': return 'text-green-600 bg-green-50 border-green-200'
      case 'caution': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'danger': return 'text-red-600 bg-red-50 border-red-200'
    }
  }

  const getRiskIcon = (level: RiskLevel) => {
    switch (level) {
      case 'safe': return <CheckCircle className="w-6 h-6" />
      case 'caution': return <Clock className="w-6 h-6" />
      case 'danger': return <AlertTriangle className="w-6 h-6" />
    }
  }

  const getRiskTitle = (level: RiskLevel) => {
    switch (level) {
      case 'safe': return '안전 단계'
      case 'caution': return '주의 단계'
      case 'danger': return '위험 단계'
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* 위험도 평가 결과 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-600" />
            위험도 평가 결과
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`p-6 border-2 rounded-lg ${getRiskColor(riskAssessment.level)}`}>
            <div className="flex items-center gap-3 mb-4">
              {getRiskIcon(riskAssessment.level)}
              <div>
                <h3 className="text-xl font-bold">{getRiskTitle(riskAssessment.level)}</h3>
                <p className="text-sm">위험도 점수: {riskAssessment.score}/100</p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold mb-2">확인된 위험 요소:</h4>
                <ul className="space-y-1">
                  {riskAssessment.factors.map((factor, index) => (
                    <li key={index} className="flex items-center gap-2 text-sm">
                      <Zap className="w-4 h-4" />
                      {factor}
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-semibold mb-2">권장 조치:</h4>
                <ul className="space-y-1">
                  {riskAssessment.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="w-4 h-4" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 최종 맞춤 서비스 추천 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Heart className="w-5 h-5 text-red-600" />
            맞춤형 복지 서비스 추천
          </CardTitle>
          <CardDescription>
            상담 내용과 위험도 평가를 종합하여 {recommendedServices.length}개의 서비스를 추천드립니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4">
            {recommendedServices.map((service, index) => (
              <div key={service.service_id} className="p-6 border rounded-lg hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="text-lg font-semibold text-gray-800 mb-1">{service.service_name}</h4>
                    <p className="text-sm text-gray-600">{service.managing_agency || service.department}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant={service.service_type === 'government' ? 'default' : 'secondary'}>
                        {service.service_type === 'government' ? '중앙부처' :
                         service.service_type === 'local' ? '지자체' : '민간'}
                      </Badge>
                      {service.category && (
                        <Badge variant="outline">{service.category}</Badge>
                      )}
                    </div>
                  </div>
                  {service.payment_method && (
                    <Badge variant="outline">{service.payment_method}</Badge>
                  )}
                </div>

                <p className="text-gray-700 mb-4">{service.service_summary}</p>

                <div className="grid md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-blue-600">지원대상:</span>
                    <p className="text-gray-600 mt-1 line-clamp-2">{service.support_target || '자세한 내용은 문의 바랍니다'}</p>
                  </div>
                  <div>
                    <span className="font-medium text-green-600">지원내용:</span>
                    <p className="text-gray-600 mt-1 line-clamp-2">{service.support_content || '자세한 내용은 문의 바랍니다'}</p>
                  </div>
                </div>

                {(service.selection_criteria || service.application_method) && (
                  <div className="grid md:grid-cols-2 gap-4 text-sm mt-3">
                    {service.selection_criteria && (
                      <div>
                        <span className="font-medium text-purple-600">선정기준:</span>
                        <p className="text-gray-600 mt-1 line-clamp-2">{service.selection_criteria}</p>
                      </div>
                    )}
                    {service.application_method && (
                      <div>
                        <span className="font-medium text-orange-600">신청방법:</span>
                        <p className="text-gray-600 mt-1 line-clamp-2">{service.application_method}</p>
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {service.support_cycle && (
                      <span className="text-xs text-gray-500">지원주기: {service.support_cycle}</span>
                    )}
                    {service.view_count > 0 && (
                      <span className="text-xs text-gray-500">조회수: {service.view_count}회</span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {service.detailed_link && (
                      <Button size="sm" variant="outline" asChild>
                        <a href={service.detailed_link} target="_blank" rel="noopener noreferrer">
                          상세보기
                        </a>
                      </Button>
                    )}
                    <Button size="sm" variant="outline">
                      신청 방법 확인
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 연락처 및 추가 안내 */}
      <Card>
        <CardHeader>
          <CardTitle>📞 추가 도움 받기</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <h4 className="font-semibold mb-2">주민센터 방문</h4>
              <p className="text-sm text-gray-600 mb-3">거주지 주민센터에서 직접 상담받으세요</p>
              <Button size="sm" variant="outline">찾아보기</Button>
            </div>

            <div className="text-center p-4 bg-green-50 rounded-lg">
              <h4 className="font-semibold mb-2">다산콜센터</h4>
              <p className="text-sm text-gray-600 mb-3">120번으로 전화상담 가능</p>
              <Button size="sm" variant="outline">전화걸기</Button>
            </div>

            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <h4 className="font-semibold mb-2">복지로 온라인</h4>
              <p className="text-sm text-gray-600 mb-3">인터넷으로 복지서비스 신청</p>
              <Button size="sm" variant="outline">사이트 이동</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 상담 완료 액션 */}
      <div className="text-center space-y-4">
        <Button size="lg" className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
          상담 결과 저장하기
        </Button>
        <div>
          <Link href="/">
            <Button variant="outline">새로운 상담 시작하기</Button>
          </Link>
        </div>
      </div>
    </div>
  )
}