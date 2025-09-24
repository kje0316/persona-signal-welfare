"use client"

import React, { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ArrowLeft, Send, MessageCircle, User, AlertCircle, RefreshCw } from 'lucide-react'
import { useSession } from '@/hooks/useSession'
import { apiClient, apiUtils, APIError } from '@/lib/api-client'

interface Message {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
  sources?: string[]
  error?: boolean
}

export default function ChatPage() {
  const { sessionId, isLoading: sessionLoading, error: sessionError, resetSession } = useSession()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: '안녕하세요! 복지 상담 AI입니다. 현재 어떤 상황으로 도움이 필요하신지 자세히 말씀해 주세요. 여러분의 상황을 정확히 파악해서 맞춤형 복지 서비스를 추천해드리겠습니다.',
      sender: 'ai',
      timestamp: new Date()
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 스크롤을 맨 아래로 이동
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 메시지 전송 함수
  const sendMessage = async () => {
    if (!inputMessage.trim() || !sessionId) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      sender: 'user',
      timestamp: new Date()
    }

    const messageContent = inputMessage
    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)
    setConnectionError(null)

    try {
      // 실제 API 호출
      const response = await apiClient.sendMessage({
        message: messageContent,
        session_id: sessionId
      })

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: response.response,
        sender: 'ai',
        timestamp: new Date(response.timestamp),
        sources: response.sources
      }

      setMessages(prev => [...prev, aiResponse])
    } catch (error) {
      console.error('메시지 전송 실패:', error)

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: error instanceof APIError
          ? `죄송합니다. 서버 연결에 문제가 있습니다: ${error.message}`
          : '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
        sender: 'ai',
        timestamp: new Date(),
        error: true
      }

      setMessages(prev => [...prev, errorMessage])
      setConnectionError(apiUtils.getErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }

  // 연결 재시도 함수
  const retryConnection = async () => {
    setConnectionError(null)
    await resetSession()
  }

  // 엔터키 처리
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col">
      {/* 헤더 */}
      <div className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="outline" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                홈으로
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-full">
                <MessageCircle className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">AI 복지 상담</h1>
                <div className="flex items-center gap-2">
                  <p className="text-sm text-gray-600">맞춤형 복지 서비스를 찾아드려요</p>
                  {sessionLoading && (
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      연결 중...
                    </div>
                  )}
                  {connectionError && (
                    <div className="flex items-center gap-1 text-xs text-red-500">
                      <AlertCircle className="w-3 h-3" />
                      연결 오류
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 채팅 영역 */}
      <div className="flex-1 overflow-hidden">
        <div className="container mx-auto px-4 py-6 h-full max-w-4xl">
          <Card className="h-full flex flex-col shadow-xl">
            {/* 메시지 목록 */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}

              {/* 로딩 표시 */}
              {isLoading && (
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-gray-100 rounded-full">
                    <MessageCircle className="w-5 h-5 text-gray-600" />
                  </div>
                  <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%]">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* 연결 오류 알림 */}
            {connectionError && (
              <div className="border-t bg-yellow-50 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-yellow-800">
                    <AlertCircle className="w-4 h-4" />
                    서버 연결에 문제가 있습니다. 네트워크를 확인해주세요.
                  </div>
                  <Button
                    onClick={retryConnection}
                    variant="outline"
                    size="sm"
                    className="text-yellow-800 border-yellow-800"
                  >
                    <RefreshCw className="w-4 h-4 mr-1" />
                    재시도
                  </Button>
                </div>
              </div>
            )}

            {/* 입력 영역 */}
            <div className="border-t bg-gray-50 p-4">
              <div className="flex gap-3">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="어떤 도움이 필요하신지 자세히 말씀해 주세요..."
                  className="flex-1 px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  disabled={isLoading || sessionLoading || !sessionId}
                />
                <Button
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || isLoading || sessionLoading || !sessionId}
                  className="px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
              <div className="mt-2 text-xs text-gray-500 text-center">
                개인정보가 포함된 내용은 안전하게 처리됩니다
                {sessionId && (
                  <span className="ml-2 text-gray-400">
                    • 세션: {sessionId.slice(0, 8)}...
                  </span>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

// 메시지 버블 컴포넌트
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.sender === 'user'

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* 아바타 */}
      <div className={`p-2 rounded-full ${
        isUser
          ? 'bg-blue-100'
          : message.error
            ? 'bg-red-100'
            : 'bg-gray-100'
      }`}>
        {isUser ? (
          <User className="w-5 h-5 text-blue-600" />
        ) : message.error ? (
          <AlertCircle className="w-5 h-5 text-red-600" />
        ) : (
          <MessageCircle className="w-5 h-5 text-gray-600" />
        )}
      </div>

      {/* 메시지 내용 */}
      <div className={`max-w-[80%] ${isUser ? 'text-right' : 'text-left'}`}>
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : message.error
                ? 'bg-red-100 text-red-800 rounded-bl-sm border border-red-200'
                : 'bg-gray-100 text-gray-800 rounded-bl-sm'
          }`}
        >
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>

        {/* 소스 정보 표시 */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 text-xs text-gray-500">
            <div className="flex items-center gap-1 mb-1">
              <MessageCircle className="w-3 h-3" />
              참고 문서:
            </div>
            <div className="pl-4 space-y-1">
              {message.sources.map((source, index) => (
                <div key={index} className="truncate">
                  • {source}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-1 text-xs text-gray-500">
          {message.timestamp.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit'
          })}
          {message.error && (
            <span className="ml-2 text-red-500">
              • 전송 실패
            </span>
          )}
        </div>
      </div>
    </div>
  )
}