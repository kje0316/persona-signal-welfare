/**
 * 세션 관리 훅
 * 로컬스토리지를 활용한 세션 ID 관리
 */

import { useState, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { apiClient, apiUtils } from '@/lib/api-client'

const SESSION_STORAGE_KEY = 'welfare_chat_session_id'

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 세션 초기화
  useEffect(() => {
    initializeSession()
  }, [])

  const initializeSession = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // 로컬스토리지에서 기존 세션 ID 확인
      const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)

      if (storedSessionId && apiUtils.isValidSessionId(storedSessionId)) {
        // 기존 세션이 유효한지 서버에서 확인
        try {
          await apiClient.getSessionData(storedSessionId)
          setSessionId(storedSessionId)
          console.log('기존 세션 복원:', storedSessionId)
          return
        } catch (error) {
          console.log('기존 세션이 유효하지 않음, 새 세션 생성')
          localStorage.removeItem(SESSION_STORAGE_KEY)
        }
      }

      // 새 세션 생성
      await createNewSession()
    } catch (error) {
      console.error('세션 초기화 실패:', error)
      setError(apiUtils.getErrorMessage(error))

      // 서버 연결 실패 시 로컬에서 UUID 생성
      const fallbackSessionId = uuidv4()
      setSessionId(fallbackSessionId)
      localStorage.setItem(SESSION_STORAGE_KEY, fallbackSessionId)
    } finally {
      setIsLoading(false)
    }
  }

  const createNewSession = async () => {
    try {
      const response = await apiClient.createSession()
      const newSessionId = response.session_id

      setSessionId(newSessionId)
      localStorage.setItem(SESSION_STORAGE_KEY, newSessionId)
      console.log('새 세션 생성:', newSessionId)
    } catch (error) {
      // 서버에서 세션 생성 실패 시 로컬에서 UUID 생성
      const fallbackSessionId = uuidv4()
      setSessionId(fallbackSessionId)
      localStorage.setItem(SESSION_STORAGE_KEY, fallbackSessionId)
      console.log('로컬 세션 생성:', fallbackSessionId)
    }
  }

  const resetSession = async () => {
    try {
      localStorage.removeItem(SESSION_STORAGE_KEY)
      await createNewSession()
      setError(null)
    } catch (error) {
      setError(apiUtils.getErrorMessage(error))
    }
  }

  const clearSession = () => {
    localStorage.removeItem(SESSION_STORAGE_KEY)
    setSessionId(null)
    setError(null)
  }

  return {
    sessionId,
    isLoading,
    error,
    resetSession,
    clearSession,
    createNewSession
  }
}