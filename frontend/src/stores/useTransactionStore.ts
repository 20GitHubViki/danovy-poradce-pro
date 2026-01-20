/**
 * Zustand store for transaction state management.
 */

import { create } from 'zustand'
import type { Transaction, TransactionType, PaginatedList } from '@/types'
import { api } from '@/services/api'

interface TransactionFilters {
  company_id: number
  type?: TransactionType
  category?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}

interface TransactionState {
  transactions: Transaction[]
  total: number
  pages: number
  currentPage: number
  pageSize: number
  isLoading: boolean
  error: string | null
  filters: Partial<TransactionFilters>

  // Actions
  fetchTransactions: (companyId: number, filters?: Partial<TransactionFilters>) => Promise<void>
  createTransaction: (data: Omit<Transaction, 'id' | 'created_at' | 'updated_at'>) => Promise<Transaction>
  updateTransaction: (id: number, data: Partial<Transaction>) => Promise<Transaction>
  deleteTransaction: (id: number) => Promise<void>
  setFilters: (filters: Partial<TransactionFilters>) => void
  setPage: (page: number) => void
  clearError: () => void
}

export const useTransactionStore = create<TransactionState>()((set, get) => ({
  transactions: [],
  total: 0,
  pages: 0,
  currentPage: 1,
  pageSize: 20,
  isLoading: false,
  error: null,
  filters: {},

  fetchTransactions: async (companyId, filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const { currentPage, pageSize } = get()
      const queryParams = new URLSearchParams({
        company_id: companyId.toString(),
        page: (filters.page || currentPage).toString(),
        page_size: (filters.page_size || pageSize).toString(),
      })

      if (filters.type) queryParams.set('type', filters.type)
      if (filters.category) queryParams.set('category', filters.category)
      if (filters.date_from) queryParams.set('date_from', filters.date_from)
      if (filters.date_to) queryParams.set('date_to', filters.date_to)

      const result = await api.get<PaginatedList<Transaction>>(
        `/transactions?${queryParams.toString()}`
      )

      set({
        transactions: result.items,
        total: result.total,
        pages: result.pages,
        currentPage: result.page,
        pageSize: result.page_size,
        filters: { ...filters, company_id: companyId },
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to fetch transactions',
        isLoading: false,
      })
    }
  },

  createTransaction: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const transaction = await api.post<Transaction>('/transactions', data)
      set((state) => ({
        transactions: [transaction, ...state.transactions],
        total: state.total + 1,
        isLoading: false,
      }))
      return transaction
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to create transaction',
        isLoading: false,
      })
      throw err
    }
  },

  updateTransaction: async (id, data) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await api.put<Transaction>(`/transactions/${id}`, data)
      set((state) => ({
        transactions: state.transactions.map((t) => (t.id === id ? updated : t)),
        isLoading: false,
      }))
      return updated
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to update transaction',
        isLoading: false,
      })
      throw err
    }
  },

  deleteTransaction: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await api.delete(`/transactions/${id}`)
      set((state) => ({
        transactions: state.transactions.filter((t) => t.id !== id),
        total: state.total - 1,
        isLoading: false,
      }))
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to delete transaction',
        isLoading: false,
      })
      throw err
    }
  },

  setFilters: (filters) => {
    set({ filters: { ...get().filters, ...filters } })
  },

  setPage: (page) => {
    set({ currentPage: page })
  },

  clearError: () => {
    set({ error: null })
  },
}))
