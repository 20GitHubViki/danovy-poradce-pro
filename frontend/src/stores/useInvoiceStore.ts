/**
 * Zustand store for invoice state management.
 */

import { create } from 'zustand'
import type { Invoice, InvoiceType, InvoiceStatus, PaginatedList } from '@/types'
import { api } from '@/services/api'

interface InvoiceFilters {
  company_id: number
  type?: InvoiceType
  status?: InvoiceStatus
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}

interface InvoiceState {
  invoices: Invoice[]
  total: number
  pages: number
  currentPage: number
  pageSize: number
  isLoading: boolean
  error: string | null
  filters: Partial<InvoiceFilters>

  // Actions
  fetchInvoices: (companyId: number, filters?: Partial<InvoiceFilters>) => Promise<void>
  createInvoice: (data: Omit<Invoice, 'id' | 'created_at' | 'updated_at'>) => Promise<Invoice>
  updateInvoice: (id: number, data: Partial<Invoice>) => Promise<Invoice>
  deleteInvoice: (id: number) => Promise<void>
  markAsPaid: (id: number, paymentDate?: string) => Promise<Invoice>
  setFilters: (filters: Partial<InvoiceFilters>) => void
  setPage: (page: number) => void
  clearError: () => void
}

export const useInvoiceStore = create<InvoiceState>()((set, get) => ({
  invoices: [],
  total: 0,
  pages: 0,
  currentPage: 1,
  pageSize: 20,
  isLoading: false,
  error: null,
  filters: {},

  fetchInvoices: async (companyId, filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const { currentPage, pageSize } = get()
      const queryParams = new URLSearchParams({
        company_id: companyId.toString(),
        page: (filters.page || currentPage).toString(),
        page_size: (filters.page_size || pageSize).toString(),
      })

      if (filters.type) queryParams.set('type', filters.type)
      if (filters.status) queryParams.set('status', filters.status)
      if (filters.date_from) queryParams.set('date_from', filters.date_from)
      if (filters.date_to) queryParams.set('date_to', filters.date_to)

      const result = await api.get<PaginatedList<Invoice>>(
        `/invoices?${queryParams.toString()}`
      )

      set({
        invoices: result.items,
        total: result.total,
        pages: result.pages,
        currentPage: result.page,
        pageSize: result.page_size,
        filters: { ...filters, company_id: companyId },
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to fetch invoices',
        isLoading: false,
      })
    }
  },

  createInvoice: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const invoice = await api.post<Invoice>('/invoices', data)
      set((state) => ({
        invoices: [invoice, ...state.invoices],
        total: state.total + 1,
        isLoading: false,
      }))
      return invoice
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to create invoice',
        isLoading: false,
      })
      throw err
    }
  },

  updateInvoice: async (id, data) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await api.put<Invoice>(`/invoices/${id}`, data)
      set((state) => ({
        invoices: state.invoices.map((i) => (i.id === id ? updated : i)),
        isLoading: false,
      }))
      return updated
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to update invoice',
        isLoading: false,
      })
      throw err
    }
  },

  deleteInvoice: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await api.delete(`/invoices/${id}`)
      set((state) => ({
        invoices: state.invoices.filter((i) => i.id !== id),
        total: state.total - 1,
        isLoading: false,
      }))
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to delete invoice',
        isLoading: false,
      })
      throw err
    }
  },

  markAsPaid: async (id, paymentDate) => {
    set({ isLoading: true, error: null })
    try {
      const queryParams = paymentDate ? `?payment_date=${paymentDate}` : ''
      const updated = await api.post<Invoice>(`/invoices/${id}/mark-paid${queryParams}`)
      set((state) => ({
        invoices: state.invoices.map((i) => (i.id === id ? updated : i)),
        isLoading: false,
      }))
      return updated
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to mark invoice as paid',
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
