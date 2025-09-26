'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Search, MessageCircle, Home, Baby, Briefcase, Utensils, Heart, BookOpen, ArrowRight, Users, Calendar, DollarSign, Bot, BarChart3, TrendingUp } from 'lucide-react'

// 복지 서비스 데이터
const welfareServices = [
  {
    icon: <Home className="w-6 h-6 text-blue-600" />,
    title: "청년 월세 지원",
    description: "만 19~39세 무주택 청년에게 월 최대 20만원까지 월세를 지원합니다. 보증금 대출도 가능합니다.",
    tags: ["청년", "주거", "월세"]
  },
  {
    icon: <Baby className="w-6 h-6 text-pink-600" />,
    title: "출산 축하금",
    description: "서울시 거주 신생아에게 첫째 200만원, 둘째 300만원, 셋째 이상 500만원을 지원합니다.",
    tags: ["출산", "육아", "지원금"]
  },
  {
    icon: <Briefcase className="w-6 h-6 text-green-600" />,
    title: "취업 지원 프로그램",
    description: "구직자를 위한 직업교육과 취업 연계 서비스를 제공합니다. 교육비 지원 포함.",
    tags: ["취업", "교육", "직업훈련"]
  },
  {
    icon: <Utensils className="w-6 h-6 text-orange-600" />,
    title: "기초생활 수급",
    description: "소득이 기준 중위소득 30% 이하인 가구에게 생계급여와 의료급여를 지원합니다.",
    tags: ["기초생활", "생계급여", "의료급여"]
  },
  {
    icon: <Heart className="w-6 h-6 text-red-600" />,
    title: "의료비 지원",
    description: "중증질환자와 저소득층에게 치료비, 수술비, 약값 등 의료비를 지원합니다.",
    tags: ["의료", "치료비", "건강"]
  },
  {
    icon: <BookOpen className="w-6 h-6 text-purple-600" />,
    title: "교육비 지원",
    description: "저소득 가정 학생에게 학비, 교재비, 급식비 등 교육 관련 비용을 지원합니다.",
    tags: ["교육", "학비", "학생"]
  }
]

// 복지 서비스 카드 컴포넌트
function WelfareServiceCard({
  icon,
  title,
  description,
  tags
}: {
  icon: React.ReactNode
  title: string
  description: string
  tags: string[]
}) {
  return (
    <Card className="group hover:shadow-lg transition-all duration-300 border-2 hover:border-blue-200">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 bg-blue-50 rounded-lg group-hover:bg-blue-100 transition-colors">
            {icon}
          </div>
          <CardTitle className="text-lg font-semibold text-gray-800 leading-tight">
            {title}
          </CardTitle>
        </div>
        <CardDescription className="text-gray-600 leading-relaxed min-h-[60px]">
          {description}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex flex-wrap gap-2 mb-4">
          {tags.map((tag, index) => (
            <Badge key={index} variant="secondary" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
        <Button
          variant="outline"
          className="w-full text-blue-600 border-blue-200 hover:bg-blue-50"
        >
          자세히 보기
        </Button>
      </CardContent>
    </Card>
  )
}

// 프로세스 스텝 컴포넌트
function ProcessStep({
  step,
  title,
  description,
  icon
}: {
  step: string
  title: string
  description: string
  icon: React.ReactNode
}) {
  return (
    <div className="text-center">
      <div className="relative">
        <div className="mx-auto mb-4 p-6 bg-gray-50 rounded-full w-20 h-20 flex items-center justify-center">
          {icon}
        </div>
        <div className="absolute -top-2 -right-2 bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">
          {step}
        </div>
      </div>
      <h3 className="text-lg font-semibold text-gray-800 mb-2">{title}</h3>
      <p className="text-gray-600 text-sm leading-relaxed">{description}</p>
    </div>
  )
}

// 사전 상담 폼 컴포넌트 - 간소화된 버전
function PreConsultationForm() {
  const [selectedGender, setSelectedGender] = useState<string>('')
  const [selectedLifeStage, setSelectedLifeStage] = useState<string>('')
  const [incomeAmount, setIncomeAmount] = useState<string>('')
  const [selectedHouseholdSize, setSelectedHouseholdSize] = useState<string>('')
  const [selectedHouseholdSituation, setSelectedHouseholdSituation] = useState<string>('')

  const handleStartConsultation = () => {
    // 선택된 조건들을 세션 스토리지에 저장
    const consultationData = {
      gender: selectedGender,
      lifeStage: selectedLifeStage,
      income: incomeAmount,
      householdSize: selectedHouseholdSize,
      householdSituation: selectedHouseholdSituation,
      timestamp: new Date().toISOString()
    }

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('preConsultationData', JSON.stringify(consultationData))
    }

    // 통합 상담 페이지로 이동
    window.location.href = '/consultation'
  }

  const isFormComplete = selectedGender && selectedLifeStage && incomeAmount && selectedHouseholdSize && selectedHouseholdSituation

  return (
    <div className="space-y-8">
      {/* 성별 선택 */}
      <div>
        <Label className="text-lg font-semibold text-gray-700 mb-4 block">
          <Users className="w-5 h-5 inline mr-2" />
          성별을 선택해주세요
        </Label>
        <RadioGroup value={selectedGender} onValueChange={setSelectedGender} className="flex gap-6">
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="male" id="gender-male" />
            <Label htmlFor="gender-male" className="cursor-pointer">남자</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="female" id="gender-female" />
            <Label htmlFor="gender-female" className="cursor-pointer">여자</Label>
          </div>
        </RadioGroup>
      </div>

      {/* 생애주기 선택 */}
      <div>
        <Label className="text-lg font-semibold text-gray-700 mb-4 block">
          <Calendar className="w-5 h-5 inline mr-2" />
          생애주기를 선택해주세요
        </Label>
        <RadioGroup value={selectedLifeStage} onValueChange={setSelectedLifeStage} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="pregnancy" id="life-pregnancy" />
            <Label htmlFor="life-pregnancy" className="cursor-pointer">출산-임신</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="infant" id="life-infant" />
            <Label htmlFor="life-infant" className="cursor-pointer">영유아</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="child" id="life-child" />
            <Label htmlFor="life-child" className="cursor-pointer">아동</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="adolescent" id="life-adolescent" />
            <Label htmlFor="life-adolescent" className="cursor-pointer">청소년</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="youth" id="life-youth" />
            <Label htmlFor="life-youth" className="cursor-pointer">청년</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="middle" id="life-middle" />
            <Label htmlFor="life-middle" className="cursor-pointer">중장년</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="senior" id="life-senior" />
            <Label htmlFor="life-senior" className="cursor-pointer">노년</Label>
          </div>
        </RadioGroup>
      </div>

      {/* 소득 입력 */}
      <div>
        <Label className="text-lg font-semibold text-gray-700 mb-4 block">
          <DollarSign className="w-5 h-5 inline mr-2" />
          연간 소득을 입력해주세요 (만원)
        </Label>
        <Input
          type="number"
          placeholder="예: 3000 (3000만원)"
          value={incomeAmount}
          onChange={(e) => setIncomeAmount(e.target.value)}
          className="text-lg p-4 border-2 focus:border-blue-500"
        />
      </div>

      {/* 가구형태 선택 */}
      <div>
        <Label className="text-lg font-semibold text-gray-700 mb-4 block">
          <Users className="w-5 h-5 inline mr-2" />
          가구형태를 선택해주세요
        </Label>
        <RadioGroup value={selectedHouseholdSize} onValueChange={setSelectedHouseholdSize} className="flex gap-6">
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="1" id="household-1" />
            <Label htmlFor="household-1" className="cursor-pointer">1인</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="2" id="household-2" />
            <Label htmlFor="household-2" className="cursor-pointer">2인</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="3" id="household-3" />
            <Label htmlFor="household-3" className="cursor-pointer">3인</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="4+" id="household-4plus" />
            <Label htmlFor="household-4plus" className="cursor-pointer">4인이상</Label>
          </div>
        </RadioGroup>
      </div>

      {/* 가구상황 선택 - 특별대상 기반 */}
      <div>
        <Label className="text-lg font-semibold text-gray-700 mb-4 block">
          <Heart className="w-5 h-5 inline mr-2" />
          가구상황을 선택해주세요
        </Label>
        <RadioGroup value={selectedHouseholdSituation} onValueChange={setSelectedHouseholdSituation} className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="single_parent" id="situation-single-parent" />
            <Label htmlFor="situation-single-parent" className="cursor-pointer">한부모·조손가정</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="disability" id="situation-disability" />
            <Label htmlFor="situation-disability" className="cursor-pointer">장애인</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="veteran" id="situation-veteran" />
            <Label htmlFor="situation-veteran" className="cursor-pointer">보훈대상자</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="multi_child" id="situation-multi-child" />
            <Label htmlFor="situation-multi-child" className="cursor-pointer">다자녀가정</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="multicultural" id="situation-multicultural" />
            <Label htmlFor="situation-multicultural" className="cursor-pointer">다문화·탈북민</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="low_income" id="situation-low-income" />
            <Label htmlFor="situation-low-income" className="cursor-pointer">저소득층</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="general" id="situation-general" />
            <Label htmlFor="situation-general" className="cursor-pointer">해당사항 없음</Label>
          </div>
        </RadioGroup>
      </div>

      {/* 상담 시작 버튼 */}
      <div className="text-center pt-6">
        <Button
          onClick={handleStartConsultation}
          disabled={!isFormComplete}
          size="lg"
          className="w-full md:w-auto px-12 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold rounded-full shadow-lg disabled:opacity-50"
        >
          <MessageCircle className="w-5 h-5 mr-2" />
          AI 맞춤 상담 시작하기
          <ArrowRight className="w-5 h-5 ml-2" />
        </Button>
        {!isFormComplete && (
          <p className="text-sm text-gray-500 mt-2">모든 항목을 선택해주세요</p>
        )}
      </div>
    </div>
  )
}

// 통합 상담 카드 컴포넌트
function IntegratedConsultationCard() {
  return (
    <Card className="consultation-card shadow-2xl border-0 mb-16 max-w-4xl mx-auto">
      <CardHeader className="text-center bg-gradient-to-r from-blue-50 to-purple-50 rounded-t-lg">
        <CardTitle className="text-3xl font-bold text-gray-800 mb-4">
          🤖 AI 맞춤 복지 상담
        </CardTitle>
        <CardDescription className="text-lg text-gray-600">
          간단한 정보 입력 후 AI와의 상담을 통해 맞춤형 복지 서비스를 찾아보세요
        </CardDescription>
      </CardHeader>
      <CardContent className="p-8">
        <PreConsultationForm />
      </CardContent>
    </Card>
  )
}

export default function HomePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      {/* 헤더 */}
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-800 mb-4">
          🧭 동행 나침반
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          복지 서비스 맞춤 매칭 플랫폼
        </p>
      </div>

      {/* 통합 상담 카드 */}
      <IntegratedConsultationCard />

      {/* 안내 섹션 */}
      <div className="text-center my-16">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          🤔 어떻게 작동하나요?
        </h2>
        <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <ProcessStep
            step="1"
            title="간단한 정보 입력"
            description="성별, 연령, 상황 등 기본 정보만 선택해주세요"
            icon={<Users className="w-8 h-8 text-blue-600" />}
          />
          <ProcessStep
            step="2"
            title="AI 맞춤 상담"
            description="상황에 맞는 AI가 추가 질문하며 정확한 분석을 진행합니다"
            icon={<MessageCircle className="w-8 h-8 text-green-600" />}
          />
          <ProcessStep
            step="3"
            title="맞춤 서비스 추천"
            description="위험도 평가와 함께 받을 수 있는 복지 서비스를 안내합니다"
            icon={<Heart className="w-8 h-8 text-red-600" />}
          />
        </div>
      </div>

      {/* AI 데이터 증강 섹션 */}
      <div className="text-center mt-16 p-12 bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 rounded-2xl border-2 border-purple-200 shadow-xl max-w-4xl mx-auto">
        <h3 className="text-3xl md:text-4xl font-bold text-gray-800 mb-6">🤖 AI 데이터 증강 시스템</h3>
        <p className="text-gray-700 mb-8 text-xl leading-relaxed max-w-3xl mx-auto">
          복지 데이터를 AI 페르소나 기반으로 분석하고 증강하여<br/>
          <span className="font-semibold text-purple-700">더 정교하고 포용적인 서비스</span>를 만들어보세요
        </p>
        <div className="grid md:grid-cols-3 gap-6 mb-8 text-sm text-gray-600">
          <div className="flex flex-col items-center p-4 bg-white/50 rounded-lg">
            <Bot className="w-8 h-8 text-purple-600 mb-2" />
            <span className="font-semibold">AI 페르소나 생성</span>
            <span className="text-xs">실제 사용자 패턴 분석</span>
          </div>
          <div className="flex flex-col items-center p-4 bg-white/50 rounded-lg">
            <BarChart3 className="w-8 h-8 text-blue-600 mb-2" />
            <span className="font-semibold">성능 분석</span>
            <span className="text-xs">데이터 품질 개선 측정</span>
          </div>
          <div className="flex flex-col items-center p-4 bg-white/50 rounded-lg">
            <TrendingUp className="w-8 h-8 text-green-600 mb-2" />
            <span className="font-semibold">추천 최적화</span>
            <span className="text-xs">개인화 서비스 향상</span>
          </div>
        </div>
        <Link href="/augmentation">
          <Button size="lg" className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold px-8 py-4 rounded-full shadow-lg">
            <Bot className="w-5 h-5 mr-2" />
            데이터 증강 시작하기
            <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
        </Link>
      </div>

      {/* 기존 페이지 연결 */}
      <div className="text-center mt-8 p-8 bg-gray-50 rounded-lg">
        <h3 className="text-xl font-bold text-gray-800 mb-4">직접 검색하고 싶으시다면</h3>
        <p className="text-gray-600 mb-6">
          조건을 직접 선택하여 복지 서비스를 검색하거나, 단순 채팅 상담도 가능합니다.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/welfare-filter">
            <Button variant="outline" className="flex items-center gap-2">
              <Search className="w-4 h-4" />
              맞춤형 복지 서비스 찾기
            </Button>
          </Link>
          <Link href="/chat">
            <Button variant="outline" className="flex items-center gap-2">
              <MessageCircle className="w-4 h-4" />
              단순 채팅 상담
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}