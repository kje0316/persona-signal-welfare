"use client"

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Search, User, Calendar, DollarSign, Home, Zap, Calculator, Info } from 'lucide-react'

// 2025년 기준 중위소득 데이터 (4인 가족 기준으로 CSV에서 확인된 값들을 역산)
const MEDIAN_INCOME_2025 = {
  1: 2308000,  // 1인가구 기준 중위소득
  2: 3822000,  // 2인가구
  3: 4945000,  // 3인가구
  4: 6096000,  // 4인가구 (CSV에서 확인: 중위소득 75% = 4,574,000원)
  5: 7130000,  // 5인가구
  6: 8164000   // 6인가구 이상
}

// 소득 구간별 지원 서비스 정보
const INCOME_SUPPORT_INFO = {
  50: { label: "생계급여 대상", services: ["생계급여", "의료급여", "주거급여", "교육급여"] },
  75: { label: "아이돌봄 가형", services: ["아이돌봄 서비스 가형", "기초생활보장"] },
  120: { label: "아이돌봄 나형", services: ["아이돌봄 서비스 나형", "교육비 지원"] },
  150: { label: "산모신생아 지원", services: ["산모신생아 건강관리", "아이돌봄 다형"] },
  200: { label: "아이돌봄 라형", services: ["아이돌봄 서비스 라형", "영유아보육료"] }
}

// 복지 서비스 데이터 타입
interface WelfareService {
  serviceId: string
  serviceName: string
  department: string
  overview: string
  targetDetails: string
  selectionCriteria: string
  supportContent: string
  supportCycle: string
  paymentMethod: string
  parsed?: {
    gender_types: string[]
    age_range: {
      min: number | null
      max: number | null
    }
    income_limits: number[]
    household_types: string[]
    special_conditions: string[]
  }
}

export default function FilterPage() {
  // 기본 필터 상태
  const [householdSize, setHouseholdSize] = useState<number>(4)
  const [monthlyIncome, setMonthlyIncome] = useState<string>('')
  const [incomePercentage, setIncomePercentage] = useState<number | null>(null)
  const [supportLevel, setSupportLevel] = useState<string | null>(null)

  // 검색 관련 상태
  const [searchResults, setSearchResults] = useState<WelfareService[]>([])
  const [isSearching, setIsSearching] = useState<boolean>(false)
  const [hasSearched, setHasSearched] = useState<boolean>(false)
  const [welfareData, setWelfareData] = useState<WelfareService[]>([])

  // 선택된 필터 상태
  const [selectedGender, setSelectedGender] = useState<string>('none')
  const [selectedAge, setSelectedAge] = useState<string>('none')
  const [selectedHousehold, setSelectedHousehold] = useState<string>('none')
  const [selectedSituations, setSelectedSituations] = useState<string[]>([])

  // 소득 입력시 실시간 계산
  useEffect(() => {
    if (monthlyIncome && householdSize) {
      const income = parseInt(monthlyIncome.replace(/,/g, '')) * 10000 // 만원 단위를 원 단위로 변환
      const medianIncome = MEDIAN_INCOME_2025[householdSize as keyof typeof MEDIAN_INCOME_2025] || MEDIAN_INCOME_2025[6]
      const percentage = Math.round((income / medianIncome) * 100)
      setIncomePercentage(percentage)

      // 지원 등급 결정
      if (percentage <= 50) setSupportLevel('50')
      else if (percentage <= 75) setSupportLevel('75')
      else if (percentage <= 120) setSupportLevel('120')
      else if (percentage <= 150) setSupportLevel('150')
      else if (percentage <= 200) setSupportLevel('200')
      else setSupportLevel('200plus')
    } else {
      setIncomePercentage(null)
      setSupportLevel(null)
    }
  }, [monthlyIncome, householdSize])

  // 숫자 포맷팅 (천 단위 콤마)
  const formatNumber = (value: string) => {
    const number = value.replace(/\D/g, '')
    return number.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  }

  const handleIncomeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatNumber(e.target.value)
    setMonthlyIncome(formatted)
  }

  // 정형화된 복지 데이터 로딩
  useEffect(() => {
    const loadWelfareData = async () => {
      try {
        const response = await fetch('/welfare_data.json')
        const data = await response.json()

        // 정형화된 데이터를 기존 인터페이스에 맞게 변환
        const services: WelfareService[] = Object.values(data.services).map((service: any) => ({
          serviceId: service.original.서비스ID,
          serviceName: service.original.서비스명,
          department: service.original.소관부처,
          overview: service.original.서비스개요,
          targetDetails: service.original.지원대상상세,
          selectionCriteria: service.original.선정기준,
          supportContent: service.original.지원내용,
          supportCycle: service.original.지원주기,
          paymentMethod: service.original.지급방식,
          // 정형화된 데이터 추가
          parsed: service.parsed
        }))

        setWelfareData(services)
        console.log(`${services.length}개의 복지 서비스 데이터 로딩 완료`)
      } catch (error) {
        console.error('복지 데이터 로딩 오류:', error)
      }
    }

    loadWelfareData()
  }, [])

  // 검색 함수 - 정형화된 데이터 활용
  const handleSearch = async () => {
    setIsSearching(true)
    setHasSearched(true)

    try {
      let filteredServices = welfareData

      // 성별 필터링
      if (selectedGender && selectedGender !== 'none') {
        filteredServices = filteredServices.filter(service => {
          if (!service.parsed?.gender_types) return true
          return service.parsed.gender_types.includes('all') ||
                 service.parsed.gender_types.includes(selectedGender)
        })
      }

      // 연령대 필터링 (사용자 나이 입력 필요 - 일단 연령대 범주로 매칭)
      if (selectedAge && selectedAge !== 'none') {
        filteredServices = filteredServices.filter(service => {
          if (!service.parsed?.age_range || (!service.parsed.age_range.min && !service.parsed.age_range.max)) return true

          const ageRange = service.parsed.age_range
          // 연령대별 범위 매핑
          let userAgeMin = 0, userAgeMax = 999
          if (selectedAge === 'infant') { userAgeMin = 0; userAgeMax = 12 }
          else if (selectedAge === 'teen') { userAgeMin = 13; userAgeMax = 24 }
          else if (selectedAge === 'young') { userAgeMin = 25; userAgeMax = 39 }
          else if (selectedAge === 'middle') { userAgeMin = 40; userAgeMax = 64 }
          else if (selectedAge === 'senior') { userAgeMin = 65; userAgeMax = 999 }

          // 나이 범위 겹침 확인
          if (ageRange.min !== null && ageRange.max !== null) {
            return !(userAgeMax < ageRange.min || userAgeMin > ageRange.max)
          }
          return true
        })
      }

      // 소득 기준 필터링 (정형화된 income_limits 사용)
      if (incomePercentage !== null) {
        filteredServices = filteredServices.filter(service => {
          if (!service.parsed?.income_limits || service.parsed.income_limits.length === 0) return true

          // 사용자 소득이 서비스의 소득 한도 이하인지 확인
          return service.parsed.income_limits.some(limit => incomePercentage <= limit)
        })
      }

      // 가구형태 필터링
      if (selectedHousehold && selectedHousehold !== 'none') {
        filteredServices = filteredServices.filter(service => {
          if (!service.parsed?.household_types || service.parsed.household_types.length === 0) return true
          return service.parsed.household_types.includes(selectedHousehold)
        })
      }

      // 특별상황 필터링
      if (selectedSituations.length > 0) {
        filteredServices = filteredServices.filter(service => {
          if (!service.parsed?.special_conditions || service.parsed.special_conditions.length === 0) return true

          // 특별상황 매핑
          const situationMap: { [key: string]: string } = {
            'situation-pregnancy': 'pregnancy',
            'situation-childcare': 'childcare',
            'situation-disability': 'disability',
            'situation-unemployment': 'unemployment',
            'situation-student': 'student',
            'situation-medical': 'medical',
            'situation-housing': 'housing',
            'situation-elderly': 'elderly',
            'situation-violence': 'violence',
            'situation-energy': 'energy'
          }

          return selectedSituations.some(situation => {
            const mappedCondition = situationMap[situation]
            return mappedCondition && service.parsed!.special_conditions.includes(mappedCondition)
          })
        })
      }

      console.log(`필터링 결과: ${filteredServices.length}개 서비스`)
      setSearchResults(filteredServices)
    } catch (error) {
      console.error('검색 오류:', error)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 헤더 */}
      <div className="text-center mb-8">
        <h1 className="text-3xl md:text-4xl font-bold text-gray-800 mb-4">
          🔍 복지 유형 선택
        </h1>
        <p className="text-lg text-gray-600 mb-6">
          조건을 선택하면 맞는 복지 서비스를 찾아드려요
        </p>
        <Link href="/">
          <Button variant="outline" className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            홈으로 돌아가기
          </Button>
        </Link>
      </div>

      {/* 필터 섹션 */}
      <Card className="shadow-xl border-0 mb-8">
        <CardHeader className="text-center bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-lg">
          <CardTitle className="text-2xl font-bold text-gray-800 mb-2">
            나의 상황을 선택해주세요
          </CardTitle>
          <CardDescription className="text-gray-600">
            더 정확한 추천을 위해 해당하는 항목을 선택해주세요
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <form className="space-y-8">
            {/* 필터 그리드 */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {/* 성별 */}
              <FilterGroup
                icon={<User className="w-6 h-6 text-blue-600" />}
                title="성별"
                id="gender"
              >
                <RadioGroup
                  value={selectedGender}
                  onValueChange={setSelectedGender}
                  className="space-y-3"
                >
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="male" id="gender-male" />
                    <Label htmlFor="gender-male" className="cursor-pointer">남성</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="female" id="gender-female" />
                    <Label htmlFor="gender-female" className="cursor-pointer">여성</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="none" id="gender-none" />
                    <Label htmlFor="gender-none" className="cursor-pointer">선택안함</Label>
                  </div>
                </RadioGroup>
              </FilterGroup>

              {/* 연령대 */}
              <FilterGroup
                icon={<Calendar className="w-6 h-6 text-green-600" />}
                title="연령대"
                id="age"
              >
                <RadioGroup
                  value={selectedAge}
                  onValueChange={setSelectedAge}
                  className="space-y-3"
                >
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="infant" id="age-infant" />
                    <Label htmlFor="age-infant" className="cursor-pointer">영유아/아동 (0-12세)</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="teen" id="age-teen" />
                    <Label htmlFor="age-teen" className="cursor-pointer">청소년 (13-24세)</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="young" id="age-young" />
                    <Label htmlFor="age-young" className="cursor-pointer">청년 (25-39세)</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="middle" id="age-middle" />
                    <Label htmlFor="age-middle" className="cursor-pointer">중장년 (40-64세)</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="senior" id="age-senior" />
                    <Label htmlFor="age-senior" className="cursor-pointer">노인 (65세 이상)</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="none" id="age-none" />
                    <Label htmlFor="age-none" className="cursor-pointer">선택안함</Label>
                  </div>
                </RadioGroup>
              </FilterGroup>

              {/* 소득 정보 입력 */}
              <FilterGroup
                icon={<Calculator className="w-6 h-6 text-purple-600" />}
                title="소득 정보"
                id="income"
                className="lg:col-span-2"
              >
                <div className="space-y-4">
                  {/* 가구원 수 선택 */}
                  <div>
                    <Label className="text-sm font-medium text-gray-700 mb-2 block">가구원 수</Label>
                    <RadioGroup
                      value={householdSize.toString()}
                      onValueChange={(value) => setHouseholdSize(parseInt(value))}
                      className="flex flex-wrap gap-3"
                    >
                      {[1, 2, 3, 4, 5, 6].map((size) => (
                        <div key={size} className="flex items-center space-x-2">
                          <RadioGroupItem value={size.toString()} id={`household-${size}`} />
                          <Label htmlFor={`household-${size}`} className="cursor-pointer text-sm">
                            {size === 6 ? '6인 이상' : `${size}인`}
                          </Label>
                        </div>
                      ))}
                    </RadioGroup>
                  </div>

                  {/* 월 소득 입력 */}
                  <div>
                    <Label htmlFor="monthly-income" className="text-sm font-medium text-gray-700 mb-2 block">
                      월 소득 (만원)
                    </Label>
                    <div className="relative">
                      <Input
                        id="monthly-income"
                        type="text"
                        value={monthlyIncome}
                        onChange={handleIncomeChange}
                        placeholder="예: 300"
                        className="pr-12"
                      />
                      <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 text-sm">
                        만원
                      </span>
                    </div>
                  </div>

                  {/* 실시간 계산 결과 */}
                  {incomePercentage !== null && supportLevel && (
                    <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="flex items-center gap-2 mb-2">
                        <Info className="w-4 h-4 text-blue-600" />
                        <span className="text-sm font-medium text-blue-800">소득 분석 결과</span>
                      </div>
                      <p className="text-sm text-blue-700 mb-2">
                        기준 중위소득 대비 <span className="font-bold">{incomePercentage}%</span>에 해당합니다
                      </p>
                      {supportLevel !== '200plus' && INCOME_SUPPORT_INFO[supportLevel as keyof typeof INCOME_SUPPORT_INFO] && (
                        <div>
                          <p className="text-sm font-medium text-blue-800 mb-1">
                            지원 가능: {INCOME_SUPPORT_INFO[supportLevel as keyof typeof INCOME_SUPPORT_INFO].label}
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {INCOME_SUPPORT_INFO[supportLevel as keyof typeof INCOME_SUPPORT_INFO].services.map((service, index) => (
                              <Badge key={index} variant="secondary" className="text-xs">{service}</Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {supportLevel === '200plus' && (
                        <p className="text-sm text-blue-700">
                          기준 중위소득을 초과하여 대부분의 소득기준 복지 서비스를 받기 어려울 수 있습니다.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </FilterGroup>

              {/* 가구 형태 */}
              <FilterGroup
                icon={<Home className="w-6 h-6 text-orange-600" />}
                title="가구 형태"
                id="household"
              >
                <RadioGroup
                  value={selectedHousehold}
                  onValueChange={setSelectedHousehold}
                  className="space-y-3"
                >
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="single" id="household-single" />
                    <Label htmlFor="household-single" className="cursor-pointer">1인가구</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="dual_worker" id="household-dual" />
                    <Label htmlFor="household-dual" className="cursor-pointer">맞벌이 가정</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="single_parent" id="household-single-parent" />
                    <Label htmlFor="household-single-parent" className="cursor-pointer">한부모가정</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="multi_child" id="household-multi-child" />
                    <Label htmlFor="household-multi-child" className="cursor-pointer">다자녀가정 (2명 이상)</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="multicultural" id="household-multicultural" />
                    <Label htmlFor="household-multicultural" className="cursor-pointer">다문화가정</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="grandparent" id="household-grandparent" />
                    <Label htmlFor="household-grandparent" className="cursor-pointer">조손가정</Label>
                  </div>
                  <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <RadioGroupItem value="none" id="household-none" />
                    <Label htmlFor="household-none" className="cursor-pointer">선택안함</Label>
                  </div>
                </RadioGroup>
              </FilterGroup>
            </div>

            {/* 특별 상황 */}
            <FilterGroup
              icon={<Zap className="w-6 h-6 text-red-600" />}
              title="특별 상황 (해당하는 모든 항목 선택)"
              id="situation"
              className="lg:col-span-3"
            >
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {specialSituations.map((situation) => (
                  <div key={situation.id} className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <Checkbox
                      id={situation.id}
                      checked={selectedSituations.includes(situation.id)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setSelectedSituations([...selectedSituations, situation.id])
                        } else {
                          setSelectedSituations(selectedSituations.filter(s => s !== situation.id))
                        }
                      }}
                    />
                    <Label htmlFor={situation.id} className="cursor-pointer text-sm">
                      {situation.label}
                    </Label>
                  </div>
                ))}
              </div>
            </FilterGroup>

            {/* 검색 버튼 */}
            <div className="text-center space-y-4 pt-6">
              <Button
                onClick={handleSearch}
                disabled={isSearching}
                size="lg"
                className="bg-blue-600 hover:bg-blue-700 text-white px-12 py-4 rounded-full text-lg font-semibold shadow-lg disabled:opacity-50"
              >
                <Search className="w-5 h-5 mr-2" />
                {isSearching ? '검색 중...' : '복지 서비스 찾기'}
              </Button>
              <div>
                <Button
                  variant="outline"
                  size="lg"
                  className="ml-4 px-8 py-2"
                  onClick={() => {
                    setSelectedGender('none')
                    setSelectedAge('none')
                    setSelectedHousehold('none')
                    setSelectedSituations([])
                    setMonthlyIncome('')
                    setHouseholdSize(4)
                    setSearchResults([])
                    setHasSearched(false)
                  }}
                >
                  초기화
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* 결과 섹션 (검색 후 표시될 영역) */}
      <Card className="shadow-xl border-0">
        <CardHeader className="text-center bg-gradient-to-r from-green-50 to-emerald-50 rounded-t-lg">
          <CardTitle className="text-2xl font-bold text-gray-800 mb-2">
            🎯 추천 복지 서비스
          </CardTitle>
          <CardDescription className="text-gray-600">
            {hasSearched ? (
              <>선택하신 조건에 맞는 <span className="font-semibold text-green-600">{searchResults.length}</span>개의 서비스를 찾았습니다</>
            ) : (
              "조건을 선택하고 검색해주세요"
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          {!hasSearched ? (
            <div className="text-center py-12 text-gray-500">
              <Search className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <p className="text-lg">조건을 선택하고 '복지 서비스 찾기' 버튼을 눌러주세요</p>
            </div>
          ) : isSearching ? (
            <div className="text-center py-12 text-gray-500">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-lg">복지 서비스를 찾고 있습니다...</p>
            </div>
          ) : searchResults.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <div className="text-6xl mb-4">😢</div>
              <p className="text-lg mb-2">선택하신 조건에 맞는 복지 서비스가 없습니다</p>
              <p className="text-sm text-gray-400">다른 조건으로 다시 검색해보세요</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* 소득 분석 결과 표시 */}
              {incomePercentage && supportLevel && (
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Calculator className="w-5 h-5 text-blue-600" />
                    <span className="font-medium text-blue-800">검색 기준</span>
                  </div>
                  <p className="text-sm text-blue-700">
                    {householdSize}인가구, 월소득 {monthlyIncome}만원 → 기준 중위소득 대비 {incomePercentage}%
                  </p>
                </div>
              )}

              {/* 복지 서비스 결과 리스트 */}
              <div className="grid gap-4">
                {searchResults.map((service, index) => (
                  <WelfareServiceResult key={service.serviceId || index} service={service} />
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// 필터 그룹 컴포넌트
function FilterGroup({
  icon,
  title,
  id,
  children,
  className = ""
}: {
  icon: React.ReactNode
  title: string
  id: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`bg-gray-50 rounded-xl p-6 border-2 border-gray-100 hover:border-gray-200 transition-colors ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-white rounded-lg shadow-sm">
          {icon}
        </div>
        <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
      </div>
      {children}
    </div>
  )
}

// 복지 서비스 결과 컴포넌트
function WelfareServiceResult({ service }: { service: WelfareService }) {
  return (
    <Card className="border-l-4 border-l-blue-500 hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg font-semibold text-gray-800 mb-1">
              {service.serviceName}
            </CardTitle>
            <p className="text-sm text-gray-600">{service.department}</p>
          </div>
          <Badge variant="outline" className="ml-2">
            {service.paymentMethod}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="text-gray-700 text-sm leading-relaxed mb-3 line-clamp-2">
          {service.overview}
        </p>
        <div className="space-y-2">
          {service.targetDetails && (
            <div>
              <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded">
                지원대상
              </span>
              <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                {service.targetDetails}
              </p>
            </div>
          )}
          {service.supportContent && (
            <div>
              <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded">
                지원내용
              </span>
              <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                {service.supportContent}
              </p>
            </div>
          )}
        </div>
        <div className="mt-4 flex items-center justify-between">
          <div className="text-xs text-gray-500">
            {service.supportCycle && `지원주기: ${service.supportCycle}`}
          </div>
          <Button size="sm" variant="outline" className="text-xs">
            자세히 보기
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// 특별 상황 데이터
const specialSituations = [
  { id: "situation-pregnancy", label: "임신/출산" },
  { id: "situation-childcare", label: "육아/돌봄 필요" },
  { id: "situation-disability", label: "장애인" },
  { id: "situation-unemployment", label: "실업/구직중" },
  { id: "situation-student", label: "학생 (교육비 지원)" },
  { id: "situation-medical", label: "의료비 지원 필요" },
  { id: "situation-housing", label: "주거 지원 필요" },
  { id: "situation-elderly", label: "노인 사회활동" },
  { id: "situation-violence", label: "폭력 피해" },
  { id: "situation-energy", label: "에너지 비용 부담" }
]