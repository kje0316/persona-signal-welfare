/**
 * API 클라이언트
 * FastAPI 서버와의 통신을 담당하는 중앙집중식 클라이언트
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1'

// API 응답 타입 정의
export interface ChatRequest {
  message: string
  session_id: string
  user_id?: string
  pre_consultation_data?: Record<string, any>
}

export interface ChatResponse {
  response: string
  session_id: string
  timestamp: string
  sources?: string[]
}

export interface ConversationHistory {
  session_id: string
  conversations: Array<{
    conversation_id: string
    user_message: string
    ai_response: string
    timestamp: string
    sources?: string[]
  }>
  total: number
}

export interface SessionData {
  session_id: string
  created_at: string
  updated_at: string
  pre_consultation_data?: Record<string, any>
  persona_match?: Record<string, any>
  risk_assessment?: Record<string, any>
}

export interface HealthStatus {
  status: string
  timestamp: string
  services: {
    rag: {
      local_rag_available: boolean
      bedrock_available: boolean
      knowledge_base_loaded: boolean
      num_documents: number
    }
    dynamodb: {
      available: boolean
      connection: boolean
    }
  }
}

// 에러 클래스
export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: any
  ) {
    super(message)
    this.name = 'APIError'
  }
}

// 기본 fetch 함수
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}/api/${API_VERSION}${endpoint}`

  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }

  try {
    const response = await fetch(url, config)

    if (!response.ok) {
      const errorData = await response.text()
      throw new APIError(
        `API request failed: ${response.status} ${response.statusText}`,
        response.status,
        errorData
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIError) {
      throw error
    }

    // 네트워크 오류 등
    throw new APIError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

// API 클라이언트 함수들
export const apiClient = {
  // 채팅 메시지 전송
  async sendMessage(data: ChatRequest): Promise<ChatResponse> {
    return apiRequest<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // 대화 이력 조회
  async getChatHistory(sessionId: string, limit: number = 10): Promise<ConversationHistory> {
    return apiRequest<ConversationHistory>(`/chat/history/${sessionId}?limit=${limit}`)
  },

  // 세션 데이터 조회
  async getSessionData(sessionId: string): Promise<SessionData> {
    return apiRequest<SessionData>(`/chat/session/${sessionId}`)
  },

  // 새 세션 생성
  async createSession(): Promise<{ session_id: string; created_at: string; message: string }> {
    return apiRequest('/chat/session', {
      method: 'POST',
    })
  },

  // 시스템 상태 확인
  async getHealthStatus(): Promise<HealthStatus> {
    return apiRequest<HealthStatus>('/health')
  },

  // 기본 health check
  async getBasicHealth(): Promise<{ status: string; service: string }> {
    return apiRequest<{ status: string; service: string }>('/../health')
  }
}

// 유틸리티 함수들
export const apiUtils = {
  // 연결 상태 확인
  async checkConnection(): Promise<boolean> {
    try {
      await apiClient.getBasicHealth()
      return true
    } catch {
      return false
    }
  },

  // 에러 메시지 추출
  getErrorMessage(error: unknown): string {
    if (error instanceof APIError) {
      return error.message
    }
    if (error instanceof Error) {
      return error.message
    }
    return '알 수 없는 오류가 발생했습니다.'
  },

  // 세션 ID가 유효한지 확인
  isValidSessionId(sessionId: string): boolean {
    // UUID v4 형식 체크 (간단한 버전)
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    return uuidRegex.test(sessionId)
  }
}