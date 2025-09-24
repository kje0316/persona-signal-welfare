'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Search, MessageCircle, Home, Baby, Briefcase, Utensils, Heart, BookOpen, ArrowRight, Users, Calendar, DollarSign, Database, Zap } from 'lucide-react'

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

// 사전 상담 폼 컴포넌트
function PreConsultationForm() {
  const [selectedGender, setSelectedGender] = useState<string>('')
  const [selectedAge, setSelectedAge] = useState<string>('')
  const [selectedSituation, setSelectedSituation] = useState<string>('')
  const [selectedIncome, setSelectedIncome] = useState<string>('')

  const handleStartConsultation = () => {
    // 선택된 조건들을 세션 스토리지에 저장
    const consultationData = {
      gender: selectedGender,
      age: selectedAge,
      situation: selectedSituation,
      income: selectedIncome,
      timestamp: new Date().toISOString()
    }

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('preConsultationData', JSON.stringify(consultationData))
    }

    // 통합 상담 페이지로 이동
    window.location.href = '/consultation'
  }

  const isFormComplete = selectedGender && selectedAge && selectedSituation && selectedIncome

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
            <Label htmlFor="gender-male" className="cursor-pointer">남성</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="female" id="gender-female" />
            <Label htmlFor="gender-female" className="cursor-pointer">여성</Label>
          </div>
        </RadioGroup>
      </div>

      {/* 연령대 선택 */}
      <div>
        <Label className="text-lg font-semibold text-gray-700 mb-4 block">
          <Calendar className="w-5 h-5 inline mr-2" />
          연령대를 선택해주세요
        </Label>
        <RadioGroup value={selectedAge} onValueChange={setSelectedAge} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="teen" id="age-teen" />
            <Label htmlFor="age-teen" className="cursor-pointer">10-20대</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="young" id="age-young" />
            <Label htmlFor="age-young" className="cursor-pointer">30대</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="middle" id="age-middle" />
            <Label htmlFor="age-middle" className="cursor-pointer">40-50대</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="senior" id="age-senior" />
            <Label htmlFor="age-senior" className="cursor-pointer">60대 이상</Label>
          </div>
        </RadioGroup>
      </div>

      {/* 주요 상황 선택 */}
      <div>
        <Label className="text-lg font-semibold text-gray-700 mb-4 block">
          <Heart className="w-5 h-5 inline mr-2" />
          현재 가장 도움이 필요한 상황을 선택해주세요
        </Label>
        <RadioGroup value={selectedSituation} onValueChange={setSelectedSituation} className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="employment" id="situation-employment" />
            <Label htmlFor="situation-employment" className="cursor-pointer">취업/일자리</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="housing" id="situation-housing" />
            <Label htmlFor="situation-housing" className="cursor-pointer">주거/월세</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="medical" id="situation-medical" />
            <Label htmlFor="situation-medical" className="cursor-pointer">의료/건강</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="childcare" id="situation-childcare" />
            <Label htmlFor="situation-childcare" className="cursor-pointer">임신/육아</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="education" id="situation-education" />
            <Label htmlFor="situation-education" className="cursor-pointer">교육/학비</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="emergency" id="situation-emergency" />
            <Label htmlFor="situation-emergency" className="cursor-pointer">긴급/위험상황</Label>
          </div>
        </RadioGroup>
      </div>

      {/* 소득 수준 선택 */}
      <div>
        <Label className="text-lg font-semibold text-gray-700 mb-4 block">
          <DollarSign className="w-5 h-5 inline mr-2" />
          가구 월 소득 수준을 선택해주세요
        </Label>
        <RadioGroup value={selectedIncome} onValueChange={setSelectedIncome} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="low" id="income-low" />
            <Label htmlFor="income-low" className="cursor-pointer">150만원 이하</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="middle-low" id="income-middle-low" />
            <Label htmlFor="income-middle-low" className="cursor-pointer">150-300만원</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="middle" id="income-middle" />
            <Label htmlFor="income-middle" className="cursor-pointer">300-500만원</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="high" id="income-high" />
            <Label htmlFor="income-high" className="cursor-pointer">500만원 이상</Label>
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
          🧭 서울 동행 나침반
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

      {/* 복지 서비스 목록 섹션 */}
      <Card className="shadow-xl border-0">
        <CardHeader className="text-center bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-lg">
          <CardTitle className="text-3xl font-bold text-gray-800 mb-2">
            📋 주요 복지 서비스
          </CardTitle>
          <CardDescription className="text-lg text-gray-600">
            서울시에서 제공하는 대표적인 복지 서비스들입니다. 위의 AI 상담을 통해 맞춤 추천을 받아보세요.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {welfareServices.map((service, index) => (
              <WelfareServiceCard key={index} {...service} />
            ))}
          </div>
          <div className="text-center mt-8">
            <p className="text-sm text-gray-600 mb-4">
              더 정확한 맞춤 서비스가 필요하시다면
            </p>
            <Button variant="outline" size="lg" onClick={() => {
              document.querySelector('.consultation-card')?.scrollIntoView({ behavior: 'smooth' })
            }}>
              AI 맞춤 상담으로 정확한 추천 받기
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* AI 데이터 증강 플랫폼 */}
      <Card className="shadow-xl border-0 mb-16">
        <CardHeader className="text-center bg-gradient-to-r from-purple-50 to-blue-50 rounded-t-lg">
          <CardTitle className="text-3xl font-bold text-gray-800 mb-2">
            🧬 범용 데이터 증강 스튜디오
          </CardTitle>
          <CardDescription className="text-lg text-gray-600">
            1차 기획서의 핵심 아이디어! 어떤 데이터든 AI 페르소나로 재탄생시키는 범용 플랫폼
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <div className="grid md:grid-cols-4 gap-6 mb-8">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <Database className="w-8 h-8 text-blue-600 mx-auto mb-3" />
              <h4 className="font-semibold mb-2">데이터 분석</h4>
              <p className="text-sm text-gray-600">CSV, Excel 파일 자동 클러스터링</p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <BookOpen className="w-8 h-8 text-purple-600 mx-auto mb-3" />
              <h4 className="font-semibold mb-2">지식 융합</h4>
              <p className="text-sm text-gray-600">PDF, 텍스트로 도메인 지식 구축</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <Users className="w-8 h-8 text-green-600 mx-auto mb-3" />
              <h4 className="font-semibold mb-2">페르소나 생성</h4>
              <p className="text-sm text-gray-600">AWS Bedrock으로 현실적 페르소나</p>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg">
              <DollarSign className="w-8 h-8 text-orange-600 mx-auto mb-3" />
              <h4 className="font-semibold mb-2">성능 향상</h4>
              <p className="text-sm text-gray-600">데이터 증강으로 12%+ 개선</p>
            </div>
          </div>

          <div className="text-center">
            <Link href="/data-augmentation">
              <Button size="lg" className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-4">
                <Zap className="w-5 h-5 mr-2" />
                데이터 증강 스튜디오 시작하기
              </Button>
            </Link>
            <p className="text-sm text-gray-500 mt-2">
              정형 데이터 + 도메인 지식 → AI 페르소나 + 증강된 데이터
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 기존 페이지 연결 */}
      <div className="text-center mt-16 p-8 bg-gray-50 rounded-lg">
        <h3 className="text-xl font-bold text-gray-800 mb-4">복지 서비스 이용하기</h3>
        <p className="text-gray-600 mb-6">
          1인가구 맞춤형 복지 서비스를 찾거나, 다양한 방식으로 상담받아보세요.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/filter">
            <Button variant="outline" className="flex items-center gap-2">
              <Search className="w-4 h-4" />
              상세 필터링 검색
            </Button>
          </Link>
          <Link href="/chat">
            <Button variant="outline" className="flex items-center gap-2">
              <MessageCircle className="w-4 h-4" />
              단순 채팅 상담
            </Button>
          </Link>
          <Link href="/personas">
            <Button variant="outline" className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              AI 페르소나 관리
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}