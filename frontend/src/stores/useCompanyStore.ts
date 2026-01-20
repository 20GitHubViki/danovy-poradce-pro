/**
 * Zustand store for company state management.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Company } from '@/types'
import { api } from '@/services/api'

interface CompanyState {
  companies: Company[]
  currentCompany: Company | null
  isLoading: boolean
  error: string | null

  // Actions
  fetchCompanies: () => Promise<void>
  setCurrentCompany: (company: Company | null) => void
  createCompany: (data: Omit<Company, 'id' | 'created_at' | 'updated_at'>) => Promise<Company>
  updateCompany: (id: number, data: Partial<Company>) => Promise<Company>
  deleteCompany: (id: number) => Promise<void>
  clearError: () => void
}

export const useCompanyStore = create<CompanyState>()(
  persist(
    (set, get) => ({
      companies: [],
      currentCompany: null,
      isLoading: false,
      error: null,

      fetchCompanies: async () => {
        set({ isLoading: true, error: null })
        try {
          const companies = await api.get<Company[]>('/companies')
          set({ companies, isLoading: false })

          // Auto-select first company if none selected
          if (!get().currentCompany && companies.length > 0) {
            set({ currentCompany: companies[0] })
          }
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch companies',
            isLoading: false,
          })
        }
      },

      setCurrentCompany: (company) => {
        set({ currentCompany: company })
      },

      createCompany: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const company = await api.post<Company>('/companies', data)
          set((state) => ({
            companies: [...state.companies, company],
            currentCompany: company,
            isLoading: false,
          }))
          return company
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to create company',
            isLoading: false,
          })
          throw err
        }
      },

      updateCompany: async (id, data) => {
        set({ isLoading: true, error: null })
        try {
          const updated = await api.put<Company>(`/companies/${id}`, data)
          set((state) => ({
            companies: state.companies.map((c) => (c.id === id ? updated : c)),
            currentCompany: state.currentCompany?.id === id ? updated : state.currentCompany,
            isLoading: false,
          }))
          return updated
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to update company',
            isLoading: false,
          })
          throw err
        }
      },

      deleteCompany: async (id) => {
        set({ isLoading: true, error: null })
        try {
          await api.delete(`/companies/${id}`)
          set((state) => ({
            companies: state.companies.filter((c) => c.id !== id),
            currentCompany: state.currentCompany?.id === id ? null : state.currentCompany,
            isLoading: false,
          }))
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to delete company',
            isLoading: false,
          })
          throw err
        }
      },

      clearError: () => {
        set({ error: null })
      },
    }),
    {
      name: 'company-storage',
      partialize: (state) => ({
        currentCompany: state.currentCompany,
      }),
    }
  )
)
