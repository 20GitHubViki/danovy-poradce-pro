import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  Clock,
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

export default function Dashboard() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', 1], // company_id = 1
    queryFn: () => api.get('/reports/dashboard/1'),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Načítám data...</div>
      </div>
    )
  }

  // Mock data for demo
  const mockData = {
    income_ytd: 450000,
    income_growth: 12.5,
    expenses_ytd: 180000,
    profit_ytd: 270000,
    estimated_tax: 56700,
    cash_flow: [
      { month: '2026-01', income: 45000, expenses: 15000, balance: 30000 },
      { month: '2026-02', income: 52000, expenses: 18000, balance: 34000 },
      { month: '2026-03', income: 48000, expenses: 22000, balance: 26000 },
      { month: '2026-04', income: 61000, expenses: 16000, balance: 45000 },
      { month: '2026-05', income: 55000, expenses: 20000, balance: 35000 },
      { month: '2026-06', income: 58000, expenses: 19000, balance: 39000 },
    ],
    pending_invoices_count: 3,
    pending_invoices_amount: 85000,
    overdue_invoices_count: 1,
    recommendations: [
      {
        category: 'tax',
        priority: 'medium',
        title: 'Daňová optimalizace',
        message: 'Zvažte výplatu dividend před koncem roku pro optimalizaci daňové zátěže.',
      },
      {
        category: 'accounting',
        priority: 'low',
        title: 'Kontrola odpisů',
        message: 'Zkontrolujte, zda jsou všechny odpisy správně zaúčtovány.',
      },
    ],
  }

  const data = dashboard || mockData

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Přehled vaší finanční situace</p>
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
            <div className="flex items-center text-green-600">
              <TrendingUp className="w-4 h-4 mr-1" />
              <span className="text-sm font-medium">
                {formatPercent(data.income_growth)}
              </span>
            </div>
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
            <p className="text-2xl font-bold text-green-600">
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
              <AreaChart data={data.cash_flow}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="month"
                  tickFormatter={(value) => value.split('-')[1]}
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
                <p className="font-bold text-red-800">
                  {data.overdue_invoices_count}
                </p>
              </div>
            )}

            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-green-800">
                  Zaplaceno tento měsíc
                </span>
              </div>
              <p className="font-bold text-green-800">12</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Recommendations */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          🤖 AI Doporučení
        </h2>
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
              <div>
                <p className="font-medium text-gray-900">{rec.title}</p>
                <p className="text-sm text-gray-600">{rec.message}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
