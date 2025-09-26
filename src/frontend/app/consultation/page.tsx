"use client"

import React, { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Send, MessageCircle, User, AlertTriangle, CheckCircle, Clock, Heart, Zap, Download } from 'lucide-react'

interface Message {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
  hasWelfareButton?: boolean
  welfareUrl?: string
  hasPDFButton?: boolean
}

interface PreConsultationData {
  gender: string
  lifeStage: string
  income: string
  householdSize: string
  householdSituation: string
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
  const [userFormData, setUserFormData] = useState({
    name: '',
    birthDate: '',
    address: '',
    phone: '',
    housingType: '',
    situation: ''
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 컴포넌트 마운트 시 세션 데이터 로드
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedData = sessionStorage.getItem('preConsultationData')
      if (storedData) {
        const data = JSON.parse(storedData)
        setPreData(data)
      }
    }
  }, [])

  // PDF 다운로드 함수 - 기존 파일 다운로드
  const generatePDF = async () => {
    try {
      // 백엔드 API를 통해 PDF 파일 다운로드
      const response = await fetch('http://localhost:8001/download-pdf/긴급지원 신청서 서식.pdf')

      if (!response.ok) {
        throw new Error('파일 다운로드에 실패했습니다.')
      }

      // Blob으로 변환
      const blob = await response.blob()

      // 다운로드 링크 생성
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = '긴급지원 신청서 서식.pdf'
      document.body.appendChild(link)
      link.click()

      // 정리
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('PDF 다운로드 오류:', error)
      alert('파일 다운로드에 실패했습니다. 잠시 후 다시 시도해주세요.')
    }
  }

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

  // 서비스 로드 완료 후 초기 AI 메시지 생성 (시나리오별 대응)
  useEffect(() => {
    if (preData && messages.length === 0) {
      // 시나리오 1: 남성, 노년, 1200, 1인, 저소득
      const isScenario1 = preData.gender === 'male' && preData.lifeStage === 'senior' &&
                         preData.income === '1200' && preData.householdSize === '1' &&
                         preData.householdSituation === 'low_income'

      // 시나리오 2: 여성, 임신, 4000, 1인, 일반
      const isScenario2 = preData.gender === 'female' && preData.lifeStage === 'pregnancy' &&
                         preData.income === '4000' && preData.householdSize === '1' &&
                         preData.householdSituation === 'general'

      let initialContent = ''
      if (isScenario1) {
        initialContent = getScenario1Response(1, '')
      } else if (isScenario2) {
        initialContent = getScenario2Response(1, '')
      } else {
        // 일반 사용자의 경우
        initialContent = `안녕하세요! 복지 전문 상담사 AI입니다. 현재 상황에 맞는 복지 서비스를 찾아드리겠습니다. 지금 어떤 이유로 복지 서비스를 찾고 계신지 간단하게 말씀해주실 수 있을까요?`
      }

      setMessages([{
        id: '1',
        content: initialContent,
        sender: 'ai',
        timestamp: new Date()
      }])
    }
  }, [preData, messages])

  // 초기 AI 메시지 생성 (시나리오별, 복지 서비스 설명 포함)
  const generateInitialMessage = (data: PreConsultationData, services: WelfareService[]): string => {
    const genderText = data.gender === 'male' ? '남성' : '여성'

    const lifeStageText = {
      'pregnancy': '출산-임신',
      'infant': '영유아',
      'child': '아동',
      'adolescent': '청소년',
      'youth': '청년',
      'middle': '중장년',
      'senior': '노년'
    }[data.lifeStage] || data.lifeStage

    const householdSizeText = {
      '1': '1인 가구',
      '2': '2인 가구',
      '3': '3인 가구',
      '4+': '4인 이상 가구'
    }[data.householdSize] || data.householdSize

    const householdSituationText = {
      'single_parent': '한부모·조손가정',
      'disability': '장애인',
      'veteran': '보훈대상자',
      'multi_child': '다자녀가정',
      'multicultural': '다문화·탈북민',
      'low_income': '저소득층',
      'general': '해당사항 없음'
    }[data.householdSituation] || data.householdSituation

    // 시나리오 판단
    const isScenario1 = data.gender === 'female' && data.lifeStage === 'pregnancy' &&
                       data.income === '4000' && data.householdSize === '1' &&
                       data.householdSituation === 'general'

    const isScenario2 = data.gender === 'male' && data.lifeStage === 'senior' &&
                       data.income === '1200' && data.householdSize === '1' &&
                       data.householdSituation === 'low_income'

    const profileSummary = `먼저 입력해주신 기본 정보를 정리해보았습니다:
👤 ${genderText} · 🎂 ${lifeStageText}
💰 연소득 ${data.income}만원 · 👥 ${householdSizeText}
🏠 ${householdSituationText}`

    if (isScenario1) {
      // 시나리오 1: 임신한 여성 - 복지 서비스 설명 포함
      const topServices = services.slice(0, 3)
      const servicesDescription = topServices.length > 0 ?
        `\n\n💡 **현재 상황에 맞는 주요 복지 서비스:**\n${topServices.map((service, index) =>
          `${index + 1}. **${service.service_name}**\n   - ${service.service_summary || '상세 설명을 위해 상담을 진행해보세요.'}`
        ).join('\n\n')}\n\n이 외에도 총 ${services.length}개의 서비스를 찾았습니다.` : ''

      return `안녕하세요! 복지 전문 상담사 AI입니다. 😊

${profileSummary}${servicesDescription}

현재 임신 중이시군요. 위 서비스들 중 어떤 것이 가장 도움이 될 것 같으신가요? 또한 임신 몇 개월 정도 되셨는지 알려주세요.`

    } else if (isScenario2) {
      // 시나리오 2: 5단계 구조 긴급복지 상담 시작
      return `안녕하세요! 복지 전문 상담사 AI입니다. 😊

${profileSummary}

지금 어떤 이유로 복지 서비스를 찾고 계신지 간단히 말씀해주실 수 있을까요?`

    } else {
      // 일반적인 상담 - 복지 서비스 설명 포함
      const topServices = services.slice(0, 3)
      const servicesDescription = topServices.length > 0 ?
        `\n\n💡 **현재 상황에 맞는 주요 복지 서비스:**\n${topServices.map((service, index) =>
          `${index + 1}. **${service.service_name}**\n   - ${service.service_summary || '상세 설명을 위해 상담을 진행해보세요.'}`
        ).join('\n\n')}\n\n이 외에도 총 ${services.length}개의 서비스를 찾았습니다.` : ''

      return `안녕하세요! 복지 전문 상담사 AI입니다. 😊

${profileSummary}${servicesDescription}

위 서비스들은 기본 조건으로 찾은 복지 서비스들입니다. 더욱 정확하고 도움이 되는 추천을 위해 현재 상황을 자세히 말씀해 주세요:

✅ 지금 가장 어려운 점이나 긴급한 도움이 필요한 부분
✅ 함께 사는 가족이나 돌봐야 할 분이 있는지
✅ 건강, 일자리, 주거 등 특별한 상황
✅ 이전에 받아본 복지 혜택이나 신청 경험

어떤 내용이든 편하게 말씀해 주세요. 차근차근 도와드리겠습니다! 💪`
    }
  }


  // 1차 필터링 서비스 로드 - 백엔드 API 사용
  const loadRecommendedServices = async (data: PreConsultationData) => {
    setIsLoadingServices(true)
    setServicesError(null)

    try {
      // 백엔드 API 엔드포인트 구성 - 새로운 필드 구조에 맞춤
      const queryParams = new URLSearchParams({
        gender: data.gender,
        lifeStage: data.lifeStage,
        income: data.income,
        householdSize: data.householdSize,
        householdSituation: data.householdSituation,
        limit: '20',
        offset: '0'
      })

      const response = await fetch(`http://localhost:8001/welfare-services?${queryParams.toString()}`)

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

    // 시나리오별 즉시 응답 (API 호출 없이)
    // 사용자 메시지만 카운트하여 올바른 단계 계산 (초기 AI 메시지 고려하여 +1)
    const userMessageCount = messages.filter(msg => msg.sender === 'user').length + 2
    const fallbackContent = generateScenarioFallback(preData, userMessageCount, inputMessage)

    // 위기상황 신고 메시지인지 확인
    const isWelfareCrisisMessage = fallbackContent.includes('바로 신고하러 가기') || fallbackContent.includes('복지위기상황 신고')
    // PDF 다운로드 메시지인지 확인
    const isPDFDownloadMessage = fallbackContent.includes('신청서 다운로드')

    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: fallbackContent.replace(/<button[\s\S]*?<\/button>/g, ''), // HTML 버튼 제거
      sender: 'ai',
      timestamp: new Date(),
      hasWelfareButton: isWelfareCrisisMessage,
      welfareUrl: 'https://www.bokjiro.go.kr/ssis-tbu/twatdc/wlfareCrisNtce/dclrPage.do',
      hasPDFButton: isPDFDownloadMessage
    }

    // 0.7초 후에 AI 메시지 표시 (생각하는 시간 시뮬레이션)
    setTimeout(() => {
      setMessages(prev => [...prev, aiMessage])
    }, 700)

    // 로딩 상태는 즉시 해제하여 사용자가 바로 다음 메시지 입력 가능
    setIsLoading(false)

    // 채팅 턴 카운트 증가
    setChatTurnCount(prev => prev + 1)

    // 위험도 평가 결과 단계로 넘어가지 않도록 주석 처리
    // if (chatTurnCount >= 4) {
    //   setTimeout(() => {
    //     const risk = assessRisk(messages.concat([userMessage]))
    //     setRiskAssessment(risk)
    //     setCurrentPhase('results')
    //   }, 2000)
    // }
  }

  // 시나리오 1 대화 로직: 남성, 노년, 1200, 1인, 저소득 (단순 순차적)
  const getScenario1Response = (messageCount: number, userInput: string): string => {
    console.log('getScenario1Response 호출됨 - messageCount:', messageCount, 'userInput:', userInput)

    // 1단계
    if (messageCount === 1) {
      return `안녕하세요. 입력하신 기본 정보를 정리해왔습니다.
남성 / 노년 / 1200만원 / 1인 / 저소득

지금 어떤 이유로 복지 서비스를 찾고 계신지 간단히 말씀해주실 수 있을까요?`
    }

    // 2단계
    if (messageCount === 2) {
      return `현재 소득이나 일자리 상황은 어떠신가요? 실직하셨거나 소득이 줄어든 상황인지 알려주세요.`
    }

    // 3단계
    if (messageCount === 3) {
      return `지금 생활하시면서 가장 불편하거나 걱정되는 부분이 한 가지 있으실까요?`
    }

    // 4단계
    if (messageCount === 4) {
      return `그동안 받아보신 복지 혜택이나 지원이 있으신가요? 기초생활수급자나 다른 복지 서비스를 이용해보셨는지 궁금합니다.`
    }

    // 5단계
    if (messageCount === 5) {
      return `네, 확인 감사합니다. 지금까지 말씀해주신 내용을 종합해볼 때, 갑작스러운 실직으로 소득이 중단되어 생계에 큰 어려움을 겪고 계신 것으로 판단됩니다.

이런 경우에는 '긴급복지 생계지원' 제도가 가장 빠르고 직접적인 도움이 될 수 있습니다. 이 서비스를 가장 추천해 드립니다.

신청 방법을 안내해 드릴까요?`
    }

    // 6단계: 좋은 선택입니다 + 신청서 작성 안내
    if (messageCount === 6) {
      return `좋은 선택입니다! 긴급복지 생계지원은 실직상황에서 가장 빠른 도움을 받을 수 있는 제도입니다.

지금 여기서 신청서를 미리 작성해드릴 수 있습니다.
아래 질문에 답해주시면 자동으로 채워집니다 ✍️

신청서 작성을 도와드릴까요?`
    }

    // 7단계부터: 신청서 작성 단계들
    if (messageCount === 7) {
      return `1️⃣ 성함을 알려주세요.`
    }

    if (messageCount === 8) {
      // 사용자 입력으로부터 이름 저장
      setUserFormData(prev => ({ ...prev, name: userInput }))
      return `2️⃣ 생년월일 8자리를 입력해주세요.
(예: 1900-01-01)`
    }

    if (messageCount === 9) {
      return `3️⃣ 현재 주소를 입력해주세요.
(예: 서울특별시 은평구 응암로 123)`
    }

    if (messageCount === 10) {
      return `4️⃣ 연락 가능한 휴대전화 번호는요?
(예: 010-1234-5678)`
    }

    if (messageCount === 11) {
      return `5️⃣ 거주 형태는 어떤가요?
(자가 / 전세 / 월세 중 선택해주세요)`
    }

    if (messageCount === 12) {
      return `6️⃣ 현재 상황을 간단히 적어주세요.
(예: 실직으로 소득 없음, 두 달 전에 실직했고 현재 소득이 전혀 없어 생활이 어렵습니다)`
    }

    // 최종 단계: 신청서 완성 및 PDF 다운로드
    if (messageCount >= 13) {
      return `✅ **감사합니다. 모든 준비가 끝났습니다.**

아래 '신청서 다운로드' 버튼을 누르시면 PDF 파일로 다운받을 수 있습니다.
주민센터 방문 시 이 신청서를 가져가시면 빠르게 처리받으실 수 있어요! 📄

**신청서 내용:**
• 긴급복지지원 신청서
• 신청인 정보 (성명, 생년월일, 주소, 연락처)
• 가구현황 및 거주형태
• 신청사유: 실직으로 인한 생계곤란
• 신청항목: 생계지원

📍 **제출처**: 거주지 주민센터 또는 복지로 온라인
⏰ **처리시간**: 신청 후 48시간 이내 1차 지원 가능

더 궁금한 점이 있으시면 언제든 말씀해주세요.`
    }

    return "상담이 완료되었습니다. 추가 질문이 있으시면 언제든 말씀해주세요."
  }

  // 시나리오 2 대화 로직: 여성, 임신, 4000, 1인, 해당사항 없음 (위기상황 판단)
  const getScenario2Response = (messageCount: number, userInput: string): string => {
    console.log('🔥 getScenario2Response 호출됨 - messageCount:', messageCount, 'userInput:', userInput)

    // 1단계: 기본 정보 확인 및 상황 파악
    if (messageCount === 1) {
      return `안녕하세요. 입력하신 기본 정보를 확인했습니다.
여성 / 임신 / 4000만원 / 1인 가구 / 해당사항 없음

현재 임신 상태에서 혼자 계신 상황이군요. 지금 가장 걱정되거나 어려운 점이 무엇인지 말씀해주세요.`
    }

    // 2단계: 건강 상태 및 지원 체계 확인
    if (messageCount === 2) {
      return `현재 정기적인 산부인과 검진은 받고 계신가요? 그리고 주변에 도움을 요청할 수 있는 가족이나 지인이 있으신지요?`
    }

    // 3단계: 경제적 상황 및 일자리 확인
    if (messageCount === 3) {
      return `임신 중 일을 계속하고 계신가요? 출산 후 경제적 계획은 어떻게 되시나요?`
    }

    // 4단계: 산전 관리 및 대비 상황 확인
    if (messageCount === 4) {
      return `산전 관리는 어떻게 하고 계신가요? 출산 준비물이나 신생아 용품은 준비해두셨나요? 그리고 응급상황 시 도움을 요청할 수 있는 분이 계신가요?`
    }

    // 5단계: 심리적 상태 및 스트레스 수준 확인
    if (messageCount === 5) {
      return `혹시 요즘 불안하거나 우울한 기분이 들 때가 있으신가요? 임신 중 혼자 있는 시간이 많아서 외롭거나 힘든 상황이 있으셨나요? 밤에 잘 주무시고 식욕은 괜찮으신가요?`
    }

    // 6단계: 생활 패턴 및 안전 상황 확인
    if (messageCount === 6) {
      return `생활 패턴에 대해 좀 더 알려주세요. 하루 종일 어떻게 보내시는지요? 그리고 혹시 집에서 넘어지거나 다칠 것 같은 상황이 발생하면 즉시 도움을 받을 수 있으신가요?`
    }

    // 7단계: 사용자 응답 후 바로 위기 상황 판단부터 사연 작성 예시까지 한 번에 제공
    if (messageCount === 7) {
      console.log('🚨 7단계 실행됨! 위기 상황 판단 메시지')
      return `말씀해주신 내용을 종합해보니 **위험한 상황으로 판단됩니다**.

복지로 **복지위기알림 신고**를 도와드리겠습니다.

복지로 위기신고 양식은 3가지 주요 항목을 작성해야 합니다:

**1️⃣ 위기상황 유형**
→ **'건강/의료'**를 선택하세요
   (임신 관련 의료지원 필요)

**2️⃣ 가구 유형**
→ **'독거가구'**를 선택하세요
   (1인 가구에 해당)

**3️⃣ 사연 작성**
**사연 작성 예시:**

"저는 20대 한부모 가정의 임산부로 현재 임신 38주차이며 출산을 며칠 앞두고 있습니다.

2025년 2월 10일에 '마포미래여성병원'에서 임신 확인을 받았으며, 출산 예정일은 2025년 10월 1일입니다.

현재 검사비와 입원비만 200만 원 이상이 발생했고, 출산 후 추가 의료비가 예상되어 감당이 어려운 상황입니다.

소득이 거의 없고 가족의 도움도 받을 수 없어 의료비 부담으로 출산 자체가 두려울 지경입니다.

의료급여 임신·출산 진료비 지원과 긴급복지 위기 지원을 통해 안전한 출산이 가능하도록 도움을 요청드립니다."

위와 같은 방식으로 구체적인 상황과 필요한 지원을 작성하시면 됩니다.`
    }

    // 8단계 이후: 복지로 사이트 연결
    if (messageCount >= 8) {
      console.log('⭐ 8단계 이후 실행됨! 신고 버튼 메시지')
      return `✅ **복지위기상황 신고를 진행해주세요**

위에서 안내드린 내용으로 양식을 작성하시면 됩니다:
• 위기상황: **건강/의료**
• 가구유형: **독거가구**
• 사연: 위에서 제공한 예시 참고

🔗 **바로 신고하러 가기**
복지로 위기상황 신고 페이지로 연결됩니다.`
    }

    return "상담이 완료되었습니다. 추가 질문이 있으시면 언제든 말씀해주세요."
  }

  // 시나리오별 폴백 응답 생성
  const generateScenarioFallback = (preData: PreConsultationData, messageCount: number, userInput: string): string => {
    console.log('generateScenarioFallback 호출됨 - preData:', preData, 'messageCount:', messageCount)

    const isScenario1 = preData.gender === 'male' && preData.lifeStage === 'senior' &&
                       preData.income === '1200' && preData.householdSize === '1' &&
                       preData.householdSituation === 'low_income'

    const isScenario2 = preData.gender === 'female' && preData.lifeStage === 'pregnancy' &&
                       preData.income === '4000' && preData.householdSize === '1' &&
                       preData.householdSituation === 'general'

    console.log('시나리오 판별 결과 - isScenario1:', isScenario1, 'isScenario2:', isScenario2)

    if (isScenario1) {
      // 시나리오 1: getScenario1Response 함수 호출 (남성, 노년, 저소득)
      console.log('generateScenarioFallback - 시나리오 1 호출됨, messageCount:', messageCount, 'userInput:', userInput)
      const response = getScenario1Response(messageCount, userInput)
      console.log('getScenario1Response 응답:', response)
      return response
    } else if (isScenario2) {
      // 시나리오 2: getScenario2Response 함수 호출 (6단계 대화 구조)
      console.log('generateScenarioFallback - 시나리오 2 호출됨, messageCount:', messageCount, 'userInput:', userInput)
      const response = getScenario2Response(messageCount, userInput)
      console.log('getScenario2Response 응답:', response)
      return response
    } else {
      // 일반적인 상담
      console.log('일반 상담으로 처리됨')
      return `죄송합니다. 일시적으로 상담 서비스에 문제가 발생했습니다.

다음 방법으로 도움받으실 수 있습니다:
📞 다산콜센터: 120 (무료)
🏢 거주지 주민센터 방문 상담
🌐 복지로 온라인: www.bokjiro.go.kr

잠시 후 다시 시도해주세요.`
    }
  }

  // AI 응답 생성 (사용되지 않음 - 제거 예정)
  const generateAIResponse = (userInput: string, turnCount: number): { content: string, shouldFinish: boolean } => {
    const input = userInput.toLowerCase()
    console.log('generateAIResponse 호출됨, userInput:', userInput, 'turnCount:', turnCount)

    // 시나리오 2 판별 (preData가 있는 경우)
    if (preData) {
      const isScenario2 = preData.gender === 'male' && preData.lifeStage === 'senior' &&
                         preData.income === '1200' && preData.householdSize === '1' &&
                         preData.householdSituation === 'low_income'

      console.log('preData 확인됨, isScenario2:', isScenario2)

      if (isScenario2) {
        // 시나리오 2: getScenario2Response 함수 호출
        console.log('generateAIResponse - 시나리오 2 호출, turnCount + 1:', turnCount + 1)
        const response = getScenario2Response(turnCount + 1, userInput) // turnCount + 1 because initial message is turnCount 0
        console.log('generateAIResponse - getScenario2Response 응답:', response)
        return {
          content: response,
          shouldFinish: false
        }
      }
    }

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
            generatePDF={generatePDF}
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
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <div className="text-xs text-gray-600">성별</div>
              <div className="font-semibold text-sm">{preData.gender === 'male' ? '남성' : '여성'}</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <div className="text-xs text-gray-600">생애주기</div>
              <div className="font-semibold text-sm">
                {{
                  'pregnancy': '출산-임신',
                  'infant': '영유아',
                  'child': '아동',
                  'adolescent': '청소년',
                  'youth': '청년',
                  'middle': '중장년',
                  'senior': '노년'
                }[preData.lifeStage] || preData.lifeStage}
              </div>
            </div>
            <div className="text-center p-3 bg-orange-50 rounded-lg">
              <div className="text-xs text-gray-600">연소득</div>
              <div className="font-semibold text-sm">{preData.income}만원</div>
            </div>
            <div className="text-center p-3 bg-purple-50 rounded-lg">
              <div className="text-xs text-gray-600">가구형태</div>
              <div className="font-semibold text-sm">
                {{
                  '1': '1인',
                  '2': '2인',
                  '3': '3인',
                  '4+': '4인+'
                }[preData.householdSize] || preData.householdSize}
              </div>
            </div>
            <div className="text-center p-3 bg-pink-50 rounded-lg">
              <div className="text-xs text-gray-600">가구상황</div>
              <div className="font-semibold text-sm">
                {{
                  'single_parent': '한부모·조손',
                  'disability': '장애인',
                  'veteran': '보훈대상자',
                  'multi_child': '다자녀',
                  'multicultural': '다문화·탈북민',
                  'low_income': '저소득층',
                  'general': '해당사항 없음'
                }[preData.householdSituation] || preData.householdSituation}
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
                <div key={service.service_id}
                     className="p-4 border rounded-lg hover:shadow-md transition-shadow cursor-pointer"
                     onClick={() => service.detailed_link && window.open(service.detailed_link, '_blank')}>
                  <h4 className="font-semibold text-gray-800 mb-2">{service.service_name}</h4>
                  <p className="text-sm text-gray-600 mb-2">{service.managing_agency || service.department}</p>
                  <p className="text-sm text-gray-700 line-clamp-2">{service.service_summary}</p>
                  <div className="flex items-center justify-between mt-2">
                    <div className="flex items-center gap-2">
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
                    {service.detailed_link && (
                      <span className="text-xs text-blue-600 hover:underline">자세히 보기 →</span>
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
  inputRef,
  generatePDF
}: {
  messages: Message[]
  inputMessage: string
  setInputMessage: (value: string) => void
  isLoading: boolean
  onSendMessage: () => void
  onKeyPress: (e: React.KeyboardEvent) => void
  messagesEndRef: React.RefObject<HTMLDivElement>
  inputRef: React.RefObject<HTMLInputElement>
  generatePDF: () => void
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

                  {/* 복지위기신고 버튼 */}
                  {message.hasWelfareButton && message.welfareUrl && (
                    <div className="mt-4">
                      <Button
                        onClick={() => window.open(message.welfareUrl, '_blank')}
                        className="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-semibold px-6 py-3 rounded-lg shadow-lg transition-all duration-200 flex items-center gap-2"
                      >
                        🚨 복지위기상황 알림 신청하기
                      </Button>
                      <p className="text-xs text-gray-600 mt-2">버튼을 클릭하면 복지로 사이트가 새 창에서 열립니다</p>
                    </div>
                  )}

                  {/* PDF 다운로드 버튼 */}
                  {message.hasPDFButton && (
                    <div className="mt-4">
                      <Button
                        onClick={generatePDF}
                        className="bg-gradient-to-r from-blue-500 to-green-600 hover:from-blue-600 hover:to-green-700 text-white font-semibold px-6 py-3 rounded-lg shadow-lg transition-all duration-200 flex items-center gap-2"
                      >
                        <Download className="w-5 h-5" />
                        신청서 다운로드 (PDF)
                      </Button>
                      <p className="text-xs text-gray-600 mt-2">버튼을 클릭하면 신청서 PDF 파일이 다운로드됩니다</p>
                    </div>
                  )}

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
            {recommendedServices.map((service) => (
              <div key={service.service_id}
                   className="p-6 border rounded-lg hover:shadow-md transition-shadow cursor-pointer"
                   onClick={() => service.detailed_link && window.open(service.detailed_link, '_blank')}>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="text-lg font-semibold text-gray-800 mb-1 hover:text-blue-600 transition-colors">
                      {service.service_name}
                    </h4>
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
                  <div className="flex flex-col gap-2">
                    {service.payment_method && (
                      <Badge variant="outline">{service.payment_method}</Badge>
                    )}
                    {service.detailed_link && (
                      <span className="text-xs text-blue-600 hover:underline">자세히 보기 →</span>
                    )}
                  </div>
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