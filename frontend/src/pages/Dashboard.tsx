import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  Clock,
  Building2,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { api } from '@/services/api'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import { useCompanyStore } from '@/stores'
import type { DashboardData } from '@/types'

export default function Dashboard() {
  const { currentCompany, fetchCompanies } = useCompanyStore()

  // Fetch companies on mount
  useEffect(() => {
    fetchCompanies()
  }, [fetchCompanies])

  const { data: dashboard, isLoading, error } = useQuery<DashboardData>({
    queryKey: ['dashboard', currentCompany?.id],
    queryFn: () => api.get(`/reports/dashboard/${currentCompany?.id}`),
    enabled: !!currentCompany?.id,
  })

  // Show company selector if no company
  if (!currentCompany) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Building2 className="w-12 h-12 text-gray-400 mb-4" />
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Žádná firma není vybrána
        </h2>
        <p className="text-gray-500 mb-4">
          Pro zobrazení dashboardu nejprve vytvořte nebo vyberte firmu.
        </p>
        <a href="/settings" className="btn-primary">
          Přejít do nastavení
        </a>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Načítám data...</div>
      </div>
    )
  }

  // Fallback mock data when API returns error (e.g., no transactions yet)
  const mockData: DashboardData = {
    income_ytd: 0,
    income_growth: 0,
    expenses_ytd: 0,
    profit_ytd: 0,
    estimated_tax: 0,
    tax_deadline: new Date(new Date().getFullYear() + 1, 3, 1).toISOString(),
    tax_paid_ytd: 0,
    cash_flow: [],
    current_balance: 0,
    pending_invoices_count: 0,
    pending_invoices_amount: 0,
    overdue_invoices_count: 0,
    overdue_invoices_amount: 0,
    recommendations: [
      {
        category: 'tip',
        priority: 'low',
        title: 'Začněte zadávat transakce',
        message: 'Přidejte své první transakce pro zobrazení přehledů a doporučení.',
      },
    ],
  }

  const data = error ? mockData : (dashboard || mockData)

  // Generate demo cash flow if empty
  const cashFlowData = data.cash_flow.length > 0 ? data.cash_flow : [
    { month: '2026-01', income: 0, expenses: 0, balance: 0 },
    { month: '2026-02', income: 0, expenses: 0, balance: 0 },
    { month: '2026-03', income: 0, expenses: 0, balance: 0 },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">
            {currentCompany.name} (IČO: {currentCompany.ico})
          </p>
        </div>
        {currentCompany.is_vat_payer && (
          <span className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full">
            Plátce DPH
          </span>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Příjmy YTD</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(data.income_ytd)}
              </p>
            </div>
            {data.income_growth !== 0 && (
              <div className={`flex items-center ${data.income_growth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {data.income_growth >= 0 ? (
                  <TrendingUp className="w-4 h-4 mr-1" />
                ) : (
                  <TrendingDown className="w-4 h-4 mr-1" />
                )}
                <span className="text-sm font-medium">
                  {formatPercent(Math.abs(data.income_growth))}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Výdaje YTD</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(data.expenses_ytd)}
              </p>
            </div>
            <TrendingDown className="w-5 h-5 text-red-500" />
          </div>
        </div>

        <div className="card">
          <div>
            <p className="text-sm text-gray-500">Zisk YTD</p>
            <p className={`text-2xl font-bold ${data.profit_ytd >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(data.profit_ytd)}
            </p>
          </div>
        </div>

        <div className="card">
          <div>
            <p className="text-sm text-gray-500">Odhadovaná daň</p>
            <p className="text-2xl font-bold text-gray-900">
              {formatCurrency(data.estimated_tax)}
            </p>
            <p className="text-xs text-gray-400 mt-1">21% DPPO</p>
          </div>
        </div>
      </div>

      {/* Charts and Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cash Flow Chart */}
        <div className="card lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Cash Flow</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={cashFlowData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="month"
                  tickFormatter={(value) => {
                    const parts = value.split('-')
                    return parts.length > 1 ? parts[1] : value
                  }}
                />
                <YAxis tickFormatter={(value) => `${value / 1000}k`} />
                <Tooltip
                  formatter={(value: number) => formatCurrency(value)}
                  labelFormatter={(label) => `Měsíc: ${label}`}
                />
                <Area
                  type="monotone"
                  dataKey="income"
                  stackId="1"
                  stroke="#22c55e"
                  fill="#bbf7d0"
                  name="Příjmy"
                />
                <Area
                  type="monotone"
                  dataKey="expenses"
                  stackId="2"
                  stroke="#ef4444"
                  fill="#fecaca"
                  name="Výdaje"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Invoice Status */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Faktury</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-yellow-600" />
                <span className="text-sm font-medium text-yellow-800">
                  Čeká na platbu
                </span>
              </div>
              <div className="text-right">
                <p className="font-bold text-yellow-800">
                  {data.pending_invoices_count}
                </p>
                <p className="text-xs text-yellow-600">
                  {formatCurrency(data.pending_invoices_amount)}
                </p>
              </div>
            </div>

            {data.overdue_invoices_count > 0 && (
              <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <span className="text-sm font-medium text-red-800">
                    Po splatnosti
                  </span>
                </div>
                <div className="text-right">
                  <p className="font-bold text-red-800">
                    {data.overdue_invoices_count}
                  </p>
                  <p className="text-xs text-red-600">
                    {formatCurrency(data.overdue_invoices_amount)}
                  </p>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-green-800">
                  Aktuální bilance
                </span>
              </div>
              <p className="font-bold text-green-800">
                {formatCurrency(data.current_balance)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Recommendations */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          AI Doporučení
        </h2>
        {data.recommendations.length > 0 ? (
          <div className="space-y-3">
            {data.recommendations.map((rec, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
              >
                <div
                  className={`px-2 py-1 text-xs font-medium rounded ${
                    rec.priority === 'high'
                      ? 'bg-red-100 text-red-700'
                      : rec.priority === 'medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {rec.category}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{rec.title}</p>
                  <p className="text-sm text-gray-600">{rec.message}</p>
                  {rec.potential_savings && (
                    <p className="text-sm text-green-600 mt-1">
                      Potenciální úspora: {formatCurrency(rec.potential_savings)}
                    </p>
                  )}
                </div>
                {rec.action_required && (
                  <span className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded">
                    Akce nutná
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">
            Žádná doporučení. Přidejte transakce pro personalizované tipy.
          </p>
        )}
      </div>
    </div>
  )
}
