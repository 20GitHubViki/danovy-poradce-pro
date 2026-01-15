/**
 * TypeScript type definitions.
 */

// Transaction types
export type TransactionType = 'income' | 'expense' | 'transfer' | 'dividend' | 'tax_payment'

export interface Transaction {
  id: number
  company_id: number
  type: TransactionType
  category: string
  subcategory?: string
  amount: number
  currency: string
  exchange_rate?: number
  amount_czk: number
  date: string
  description: string
  note?: string
  debit_account: string
  credit_account: string
  source: string
  is_tax_deductible: boolean
  vat_rate?: number
  vat_amount?: number
  document_id?: number
  created_at: string
  updated_at: string
}

// Invoice types
export type InvoiceType = 'issued' | 'received'
export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled'

export interface InvoiceItem {
  id: number
  invoice_id: number
  description: string
  quantity: number
  unit: string
  unit_price: number
  vat_rate: number
  total_price: number
}

export interface Invoice {
  id: number
  company_id: number
  type: InvoiceType
  number: string
  variable_symbol?: string
  partner_name: string
  partner_ico?: string
  partner_dic?: string
  partner_address?: string
  issue_date: string
  due_date: string
  taxable_date?: string
  payment_date?: string
  subtotal: number
  vat_amount: number
  total_amount: number
  currency: string
  status: InvoiceStatus
  description?: string
  note?: string
  items: InvoiceItem[]
  created_at: string
  updated_at: string
}

// Company types
export interface Company {
  id: number
  name: string
  ico: string
  dic?: string
  address: string
  bank_account?: string
  email?: string
  phone?: string
  website?: string
  is_vat_payer: boolean
  accounting_type: 'podvojne' | 'danove_evidence'
  created_at: string
  updated_at: string
}

// Report types
export interface CashFlowEntry {
  month: string
  income: number
  expenses: number
  balance: number
}

export interface RecommendationItem {
  category: string
  priority: 'high' | 'medium' | 'low'
  title: string
  message: string
  potential_savings?: number
  action_required?: boolean
  deadline?: string
}

export interface DashboardData {
  income_ytd: number
  income_growth: number
  expenses_ytd: number
  profit_ytd: number
  estimated_tax: number
  tax_deadline: string
  tax_paid_ytd: number
  cash_flow: CashFlowEntry[]
  current_balance: number
  pending_invoices_count: number
  pending_invoices_amount: number
  overdue_invoices_count: number
  overdue_invoices_amount: number
  recommendations: RecommendationItem[]
}

// Tax types
export interface TaxProjection {
  year: number
  estimated_profit: number
  corporate_tax: number
  corporate_tax_rate: number
  net_profit: number
  dividend_withholding: number
  dividend_withholding_rate: number
  net_dividend: number
  effective_tax_rate: number
  notes: string[]
}

export interface DividendAnalysis {
  profit_before_tax: number
  dividend_corporate_tax: number
  dividend_withholding: number
  dividend_net: number
  dividend_total_tax: number
  dividend_effective_rate: number
  salary_gross: number
  salary_social_insurance: number
  salary_health_insurance: number
  salary_income_tax: number
  salary_net: number
  salary_total_cost: number
  salary_effective_rate: number
  recommended: 'dividend' | 'salary'
  reasoning: string
  potential_savings: number
}

// Pagination
export interface PaginatedList<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}
