/**
 * 用户认证状态管理
 */
import { create } from 'zustand'
import { authApi } from '../services/api'

export interface UserInfo {
  user_id: string
  username: string
  email?: string
  role: string
}

interface AuthState {
  token: string | null
  user: UserInfo | null
  isAuthenticated: boolean
  isLoading: boolean

  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, email?: string) => Promise<void>
  logout: () => void
  loadFromStorage: () => void
  fetchMe: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: false,

  login: async (username: string, password: string) => {
    const response: any = await authApi.login(username, password)
    const { access_token, user_id, username: name, role } = response

    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify({ user_id, username: name, role }))

    set({
      token: access_token,
      user: { user_id, username: name, role },
      isAuthenticated: true,
    })
  },

  register: async (username: string, password: string, email?: string) => {
    const response: any = await authApi.register(username, password, email)
    const { access_token, user_id, username: name, role } = response

    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify({ user_id, username: name, role }))

    set({
      token: access_token,
      user: { user_id, username: name, role },
      isAuthenticated: true,
    })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ token: null, user: null, isAuthenticated: false })
  },

  loadFromStorage: () => {
    const token = localStorage.getItem('token')
    const userStr = localStorage.getItem('user')

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr)
        set({ token, user, isAuthenticated: true })
      } catch {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    }
  },

  fetchMe: async () => {
    try {
      set({ isLoading: true })
      const response: any = await authApi.me()
      set({ user: response, isLoading: false })
    } catch {
      // token 过期或无效
      get().logout()
      set({ isLoading: false })
    }
  },
}))
