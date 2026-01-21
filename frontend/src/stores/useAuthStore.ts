/**
 * Authentication store using Zustand.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  is_verified: boolean
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  setTokens: (accessToken: string, refreshToken: string) => void
  setUser: (user: User) => void
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<boolean>
  fetchUser: () => Promise<void>
  clearError: () => void
}

const BASE_URL = '/api/v1'

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken, isAuthenticated: true })
      },

      setUser: (user) => {
        set({ user })
      },

      login: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Přihlášení selhalo')
          }

          const data = await response.json()
          set({
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })

          // Fetch user data
          await get().fetchUser()
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Přihlášení selhalo',
          })
          throw error
        }
      },

      register: async (email, password, fullName) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, full_name: fullName }),
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Registrace selhala')
          }

          // Auto-login after registration
          await get().login(email, password)
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Registrace selhala',
          })
          throw error
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        })
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get()
        if (!refreshToken) return false

        try {
          const response = await fetch(`${BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${refreshToken}`,
            },
          })

          if (!response.ok) {
            get().logout()
            return false
          }

          const data = await response.json()
          set({
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          })
          return true
        } catch {
          get().logout()
          return false
        }
      },

      fetchUser: async () => {
        const { accessToken } = get()
        if (!accessToken) return

        try {
          const response = await fetch(`${BASE_URL}/auth/me`, {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          })

          if (!response.ok) {
            if (response.status === 401) {
              // Try to refresh token
              const refreshed = await get().refreshAccessToken()
              if (refreshed) {
                await get().fetchUser()
                return
              }
            }
            throw new Error('Nepodařilo se načíst uživatele')
          }

          const user = await response.json()
          set({ user })
        } catch (error) {
          console.error('Failed to fetch user:', error)
        }
      },

      clearError: () => {
        set({ error: null })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
