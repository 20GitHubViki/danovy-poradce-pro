/**
 * Zustand store for application settings.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AIStatus {
  configured: boolean
  model: string
  features: {
    analysis: boolean
    dividend_vs_salary: boolean
    recommendations: boolean
    compliance_check: boolean
    tax_concepts: boolean
    tax_deadlines: boolean
  }
}

interface SettingsState {
  // UI Settings
  theme: 'light' | 'dark' | 'system'
  language: 'cs' | 'en'
  currency: 'CZK' | 'EUR' | 'USD'
  dateFormat: 'DD.MM.YYYY' | 'YYYY-MM-DD' | 'MM/DD/YYYY'

  // AI Settings
  aiStatus: AIStatus | null
  useAI: boolean

  // Tax Settings
  defaultTaxYear: number

  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setLanguage: (language: 'cs' | 'en') => void
  setCurrency: (currency: 'CZK' | 'EUR' | 'USD') => void
  setDateFormat: (format: 'DD.MM.YYYY' | 'YYYY-MM-DD' | 'MM/DD/YYYY') => void
  setUseAI: (useAI: boolean) => void
  setDefaultTaxYear: (year: number) => void
  fetchAIStatus: () => Promise<void>
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'light',
      language: 'cs',
      currency: 'CZK',
      dateFormat: 'DD.MM.YYYY',
      aiStatus: null,
      useAI: true,
      defaultTaxYear: new Date().getFullYear(),

      setTheme: (theme) => set({ theme }),
      setLanguage: (language) => set({ language }),
      setCurrency: (currency) => set({ currency }),
      setDateFormat: (dateFormat) => set({ dateFormat }),
      setUseAI: (useAI) => set({ useAI }),
      setDefaultTaxYear: (defaultTaxYear) => set({ defaultTaxYear }),

      fetchAIStatus: async () => {
        try {
          const response = await fetch('/api/v1/ai/status')
          if (response.ok) {
            const aiStatus = await response.json()
            set({ aiStatus })
          }
        } catch {
          // AI status check failed, keep existing state
        }
      },
    }),
    {
      name: 'settings-storage',
      partialize: (state) => ({
        theme: state.theme,
        language: state.language,
        currency: state.currency,
        dateFormat: state.dateFormat,
        useAI: state.useAI,
        defaultTaxYear: state.defaultTaxYear,
      }),
    }
  )
)
