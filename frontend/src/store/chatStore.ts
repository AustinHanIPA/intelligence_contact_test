/**
 * 聊天状态管理
 */
import { create } from 'zustand'
import { chatApi } from '../services/api'
import { useAuthStore } from './authStore'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  buttons?: Array<{ label: string; action: string; params?: Record<string, any> }>
  intent?: string
  emotion?: string
  handoff?: boolean
  metadata?: Record<string, any>
}

interface ChatState {
  messages: Message[]
  sessionId: string | null
  userId: string
  isLoading: boolean
  error: string | null

  sendMessage: (content: string) => Promise<void>
  executeAction: (actionId: string, params?: Record<string, any>) => Promise<void>
  clearMessages: () => void
  setUserId: (userId: string) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  sessionId: null,
  userId: 'user_001', // 默认用户
  isLoading: false,
  error: null,

  sendMessage: async (content: string) => {
    const { sessionId, userId } = get()
    // 优先使用认证用户ID
    const authUser = useAuthStore.getState().user
    const effectiveUserId = authUser?.user_id || userId

    // 添加用户消息
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }
    set((state) => ({ messages: [...state.messages, userMessage], isLoading: true, error: null }))

    try {
      const response: any = await chatApi.sendMessage({
        session_id: sessionId || undefined,
        user_id: effectiveUserId,
        message: content,
      })

      // 添加系统回复
      const assistantMessage: Message = {
        id: `msg_${Date.now()}_resp`,
        role: response.handoff ? 'system' : 'assistant',
        content: response.message,
        timestamp: response.timestamp || new Date().toISOString(),
        buttons: response.buttons,
        intent: response.intent,
        emotion: response.emotion,
        handoff: response.handoff,
        metadata: response.metadata,
      }

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        sessionId: response.session_id,
        isLoading: false,
      }))
    } catch (error: any) {
      set({
        isLoading: false,
        error: error.response?.data?.detail || '发送消息失败，请重试',
      })
    }
  },

  executeAction: async (actionId: string, params?: Record<string, any>) => {
    const { sessionId } = get()
    if (!sessionId) return

    set({ isLoading: true })

    try {
      const response: any = await chatApi.executeAction(sessionId, actionId, params)

      const actionMessage: Message = {
        id: `msg_${Date.now()}_action`,
        role: response.handoff ? 'system' : 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
        buttons: response.buttons,
        handoff: response.handoff,
      }

      set((state) => ({
        messages: [...state.messages, actionMessage],
        isLoading: false,
      }))
    } catch (error: any) {
      set({
        isLoading: false,
        error: error.response?.data?.detail || '操作执行失败',
      })
    }
  },

  clearMessages: () => set({ messages: [], sessionId: null, error: null }),

  setUserId: (userId: string) => set({ userId }),
}))
