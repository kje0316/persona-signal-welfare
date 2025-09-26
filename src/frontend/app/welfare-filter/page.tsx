'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Search, Filter, Users, DollarSign, Home, Briefcase, Heart, MapPin } from 'lucide-react'

// 실제 데이터 분석 결과 기반 필터링 옵션
const FILTER_OPTIONS = {
  age: {
    type: "select",
    options: [
      { value: "child", label: "아동·청소년 (18세 이하)", count: "1,915개 서비스" },
      { value: "youth", label: "청년 (19-39세)", count: "630개 서비스" },
      { value: "middle", label: "중장년 (40-64세)", count: "20개 서비스" },
      { value: "senior", label: "노인 (65세 이상)", count: "1,081개 서비스" },
      { value: "all", label: "연령 무관", count: "" }
    ]
  },
  income: {
    type: "select",
    options: [
      { value: "basic", label: "기초생활수급자", count: "1,222개 서비스" },
      { value: "near_poor", label: "차상위계층", count: "1,088개 서비스" },
      { value: "low_50", label: "기준중위소득 50% 이하", count: "187개 서비스" },
      { value: "low_100", label: "기준중위소득 100% 이하", count: "171개 서비스" },
      { value: "low_150", label: "기준중위소득 150% 이하", count: "296개 서비스" },
      { value: "middle_income", label: "중간소득층", count: "" },
      { value: "all", label: "소득 무관", count: "" }
    ]
  },
  family: {
    type: "checkbox",
    options: [
      { value: "single_parent", label: "한부모 가정", count: "973개 서비스" },
      { value: "multi_child", label: "다자녀 가정", count: "246개 서비스" },
      { value: "single", label: "1인 가구", count: "348개 서비스" },
      { value: "multicultural", label: "다문화 가정", count: "237개 서비스" },
      { value: "grandparent", label: "조손 가정", count: "162개 서비스" },
      { value: "defector", label: "탈북민 가정", count: "92개 서비스" }
    ]
  },
  housing: {
    type: "select",
    options: [
      { value: "owned", label: "자가 소유", count: "820개 서비스" },
      { value: "rental", label: "임대주택 거주", count: "316개 서비스" },
      { value: "homeless", label: "무주택자", count: "270개 서비스" },
      { value: "jeonse", label: "전세 거주", count: "203개 서비스" },
      { value: "monthly_rent", label: "월세 거주", count: "177개 서비스" },
      { value: "all", label: "주거형태 무관", count: "" }
    ]
  },
  special_condition: {
    type: "checkbox",
    options: [
      { value: "disability", label: "장애인", count: "405개 서비스" },
      { value: "veteran", label: "국가유공자", count: "389개 서비스" },
      { value: "pregnancy", label: "임신/출산/육아", count: "159개 서비스" },
      { value: "disease", label: "질환자 (암, 중증질환 등)", count: "질환별 상이" },
      { value: "medical", label: "의료지원 필요", count: "809개 서비스" },
      { value: "none", label: "해당사항 없음", count: "" }
    ]
  }
}

interface FilterState {
  age: string
  income: string
  family: string[]
  housing: string
  special_condition: string[]
}

export default function WelfareFilterPage() {
  const [filters, setFilters] = useState<FilterState>({
    age: '',
    income: '',
    family: [],
    housing: '',
    special_condition: []
  })

  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // 체크박스 상태 변경 핸들러
  const handleCheckboxChange = (category: 'family' | 'special_condition', value: string, checked: boolean) => {
    setFilters(prev => ({
      ...prev,
      [category]: checked
        ? [...prev[category], value]
        : prev[category].filter(item => item !== value)
    }))
  }

  // 라디오 버튼 상태 변경 핸들러
  const handleRadioChange = (category: 'age' | 'income' | 'housing', value: string) => {
    setFilters(prev => ({
      ...prev,
      [category]: value
    }))
  }

  // 검색 실행
  const handleSearch = async () => {
    setIsSearching(true)
    setHasSearched(true)

    // TODO: 실제 API 호출로 교체
    try {
      // 임시 검색 결과
      const mockResults = [
        {
          id: 1,
          service_name: "청년 월세 지원 사업",
          managing_agency: "서울시",
          category: "주거지원",
          support_content: "만 19~39세 무주택 청년에게 월 최대 20만원 월세 지원",
          detailed_link: "#"
        },
        {
          id: 2,
          service_name: "기초생활수급 생계급여",
          managing_agency: "보건복지부",
          category: "생계지원",
          support_content: "생계를 유지할 능력이 없는 가구에 최저생활 보장",
          detailed_link: "#"
        }
      ]

      setTimeout(() => {
        setSearchResults(mockResults)
        setIsSearching(false)
      }, 1000)

    } catch (error) {
      console.error('검색 오류:', error)
      setIsSearching(false)
    }
  }

  // 필터 초기화
  const resetFilters = () => {
    setFilters({
      age: '',
      income: '',
      family: [],
      housing: '',
      special_condition: []
    })
    setSearchResults([])
    setHasSearched(false)
  }

  // 선택된 필터 개수
  const selectedFiltersCount = Object.values(filters).flat().filter(Boolean).length

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          🎯 맞춤형 복지 서비스 찾기
        </h1>
        <p className="text-xl text-gray-600">
          총 5,259개 복지 서비스 중 나에게 맞는 서비스를 찾아보세요
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* 필터 섹션 */}
        <div className="lg:col-span-1">
          <Card className="sticky top-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Filter className="w-5 h-5" />
                맞춤 조건 선택
              </CardTitle>
              <CardDescription>
                본인의 상황에 해당하는 조건을 선택하세요
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 연령대 */}
              <div>
                <Label className="text-lg font-semibold text-gray-700 mb-3 block">
                  <Users className="w-5 h-5 inline mr-2" />
                  연령대
                </Label>
                <RadioGroup
                  value={filters.age}
                  onValueChange={(value) => handleRadioChange('age', value)}
                  className="space-y-2"
                >
                  {FILTER_OPTIONS.age.options.map((option) => (
                    <div key={option.value} className="flex items-center justify-between space-x-2">
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value={option.value} id={`age-${option.value}`} />
                        <Label htmlFor={`age-${option.value}`} className="cursor-pointer">
                          {option.label}
                        </Label>
                      </div>
                      {option.count && (
                        <Badge variant="secondary" className="text-xs">
                          {option.count}
                        </Badge>
                      )}
                    </div>
                  ))}
                </RadioGroup>
              </div>

              {/* 소득 수준 */}
              <div>
                <Label className="text-lg font-semibold text-gray-700 mb-3 block">
                  <DollarSign className="w-5 h-5 inline mr-2" />
                  소득 수준
                </Label>
                <RadioGroup
                  value={filters.income}
                  onValueChange={(value) => handleRadioChange('income', value)}
                  className="space-y-2"
                >
                  {FILTER_OPTIONS.income.options.map((option) => (
                    <div key={option.value} className="flex items-center justify-between space-x-2">
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value={option.value} id={`income-${option.value}`} />
                        <Label htmlFor={`income-${option.value}`} className="cursor-pointer">
                          {option.label}
                        </Label>
                      </div>
                      {option.count && (
                        <Badge variant="secondary" className="text-xs">
                          {option.count}
                        </Badge>
                      )}
                    </div>
                  ))}
                </RadioGroup>
              </div>

              {/* 가구 상황 */}
              <div>
                <Label className="text-lg font-semibold text-gray-700 mb-3 block">
                  <Home className="w-5 h-5 inline mr-2" />
                  가구 상황 (중복 선택 가능)
                </Label>
                <div className="space-y-2">
                  {FILTER_OPTIONS.family.options.map((option) => (
                    <div key={option.value} className="flex items-center justify-between space-x-2">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id={`family-${option.value}`}
                          checked={filters.family.includes(option.value)}
                          onCheckedChange={(checked) =>
                            handleCheckboxChange('family', option.value, checked as boolean)
                          }
                        />
                        <Label htmlFor={`family-${option.value}`} className="cursor-pointer">
                          {option.label}
                        </Label>
                      </div>
                      {option.count && (
                        <Badge variant="secondary" className="text-xs">
                          {option.count}
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* 주거 상황 */}
              <div>
                <Label className="text-lg font-semibold text-gray-700 mb-3 block">
                  <MapPin className="w-5 h-5 inline mr-2" />
                  주거 상황
                </Label>
                <RadioGroup
                  value={filters.housing}
                  onValueChange={(value) => handleRadioChange('housing', value)}
                  className="space-y-2"
                >
                  {FILTER_OPTIONS.housing.options.map((option) => (
                    <div key={option.value} className="flex items-center justify-between space-x-2">
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value={option.value} id={`housing-${option.value}`} />
                        <Label htmlFor={`housing-${option.value}`} className="cursor-pointer">
                          {option.label}
                        </Label>
                      </div>
                      {option.count && (
                        <Badge variant="secondary" className="text-xs">
                          {option.count}
                        </Badge>
                      )}
                    </div>
                  ))}
                </RadioGroup>
              </div>

              {/* 특수 상황 */}
              <div>
                <Label className="text-lg font-semibold text-gray-700 mb-3 block">
                  <Heart className="w-5 h-5 inline mr-2" />
                  특수 상황 (중복 선택 가능)
                </Label>
                <div className="space-y-2">
                  {FILTER_OPTIONS.special_condition.options.map((option) => (
                    <div key={option.value} className="flex items-center justify-between space-x-2">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id={`special-${option.value}`}
                          checked={filters.special_condition.includes(option.value)}
                          onCheckedChange={(checked) =>
                            handleCheckboxChange('special_condition', option.value, checked as boolean)
                          }
                        />
                        <Label htmlFor={`special-${option.value}`} className="cursor-pointer">
                          {option.label}
                        </Label>
                      </div>
                      {option.count && (
                        <Badge variant="secondary" className="text-xs">
                          {option.count}
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* 검색 버튼 */}
              <div className="flex gap-2 pt-4">
                <Button
                  onClick={handleSearch}
                  disabled={isSearching || selectedFiltersCount === 0}
                  className="flex-1"
                >
                  {isSearching ? (
                    <>검색 중...</>
                  ) : (
                    <>
                      <Search className="w-4 h-4 mr-2" />
                      맞춤 서비스 찾기 ({selectedFiltersCount})
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={resetFilters}
                  disabled={selectedFiltersCount === 0}
                >
                  초기화
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 검색 결과 섹션 */}
        <div className="lg:col-span-2">
          {!hasSearched ? (
            <Card className="h-96 flex items-center justify-center">
              <CardContent className="text-center">
                <Search className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-600 mb-2">
                  조건을 선택하고 검색해보세요
                </h3>
                <p className="text-gray-500">
                  좌측에서 본인의 상황에 맞는 조건을 선택한 후 '맞춤 서비스 찾기' 버튼을 눌러주세요
                </p>
              </CardContent>
            </Card>
          ) : (
            <div>
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-800 mb-2">
                  검색 결과 ({searchResults.length}개)
                </h2>
                <p className="text-gray-600">
                  선택하신 조건에 맞는 복지 서비스입니다
                </p>
              </div>

              {isSearching ? (
                <div className="space-y-4">
                  {[1, 2, 3].map(i => (
                    <Card key={i} className="animate-pulse">
                      <CardContent className="p-6">
                        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                        <div className="h-3 bg-gray-200 rounded w-1/4 mb-4"></div>
                        <div className="h-3 bg-gray-200 rounded w-full mb-2"></div>
                        <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : searchResults.length > 0 ? (
                <div className="space-y-4">
                  {searchResults.map((service) => (
                    <Card key={service.id} className="hover:shadow-lg transition-shadow">
                      <CardContent className="p-6">
                        <div className="flex justify-between items-start mb-3">
                          <h3 className="text-xl font-semibold text-gray-800">
                            {service.service_name}
                          </h3>
                          <Badge variant="secondary">
                            {service.category}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-500 mb-3">
                          {service.managing_agency}
                        </p>
                        <p className="text-gray-700 mb-4">
                          {service.support_content}
                        </p>
                        <Button variant="outline" className="w-full">
                          자세히 보기
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <Card>
                  <CardContent className="p-12 text-center">
                    <div className="text-6xl mb-4">🔍</div>
                    <h3 className="text-xl font-semibold text-gray-600 mb-2">
                      조건에 맞는 서비스가 없습니다
                    </h3>
                    <p className="text-gray-500 mb-4">
                      다른 조건으로 다시 검색해보시거나, 조건을 완화해보세요
                    </p>
                    <Button onClick={resetFilters} variant="outline">
                      조건 다시 설정하기
                    </Button>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}