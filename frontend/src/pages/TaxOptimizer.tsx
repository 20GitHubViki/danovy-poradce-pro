import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Calculator, TrendingUp, AlertCircle } from 'lucide-react'
import { api } from '@/services/api'
import { formatCurrency, formatPercent } from '@/utils/formatters'

export default function TaxOptimizer() {
  const [profit, setProfit] = useState('')
  const [otherIncome, setOtherIncome] = useState('')

  const { mutate: analyze, data: result, isPending } = useMutation({
    mutationFn: (params: { available_profit: number; other_income: number }) =>
      api.post('/tax/dividend-vs-salary', params),
  })

  // Mock result for demo
  const mockResult = {
    dividend: {
      net_amount: 263250,
      total_tax: 86750,
      effective_rate: 0.2479,
    },
    salary: {
      net_amount: 241500,
      total_tax: 108500,
      effective_rate: 0.31,
      employer_cost: 467200,
    },
    recommendation: {
      better_option: 'dividend',
      savings: 21750,
      reasoning:
        'Při zisku 350 000 Kč je výhodnější dividenda. Úspora: 21 750 Kč.',
    },
  }

  const analysisResult = result || (profit ? mockResult : null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    analyze({
      available_profit: parseFloat(profit) || 0,
      other_income: parseFloat(otherIncome) || 0,
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Daňový optimalizátor</h1>
        <p className="text-gray-500">
          Porovnání variant výplaty zisku: dividenda vs. mzda
        </p>
      </div>

      {/* Input Form */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Vstupní parametry
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Zisk s.r.o. (před zdaněním)</label>
              <div className="relative">
                <input
                  type="number"
                  value={profit}
                  onChange={(e) => setProfit(e.target.value)}
                  placeholder="350000"
                  className="input w-full pr-12"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  Kč
                </span>
              </div>
            </div>
            <div>
              <label className="label">Ostatní příjmy FO (ze zaměstnání)</label>
              <div className="relative">
                <input
                  type="number"
                  value={otherIncome}
                  onChange={(e) => setOtherIncome(e.target.value)}
                  placeholder="0"
                  className="input w-full pr-12"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  Kč
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Pro výpočet solidární daně
              </p>
            </div>
          </div>
          <button type="submit" disabled={isPending} className="btn-primary">
            {isPending ? 'Analyzuji...' : 'Analyzovat'}
          </button>
        </form>
      </div>

      {/* Results */}
      {analysisResult && (
        <>
          {/* Comparison Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Dividend */}
            <div
              className={`card border-2 ${
                analysisResult.recommendation.better_option === 'dividend'
                  ? 'border-green-500'
                  : 'border-transparent'
              }`}
            >
              {analysisResult.recommendation.better_option === 'dividend' && (
                <div className="flex items-center gap-2 text-green-600 mb-3">
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-sm font-medium">Doporučeno</span>
                </div>
              )}
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                💰 Dividenda
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-500">Čistá částka</span>
                  <span className="font-bold text-gray-900">
                    {formatCurrency(analysisResult.dividend.net_amount)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Celková daň</span>
                  <span className="text-gray-700">
                    {formatCurrency(analysisResult.dividend.total_tax)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Efektivní sazba</span>
                  <span className="text-gray-700">
                    {formatPercent(analysisResult.dividend.effective_rate * 100)}
                  </span>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-gray-200 text-xs text-gray-500">
                <p>21% DPPO + 15% srážková daň z dividendy</p>
              </div>
            </div>

            {/* Salary */}
            <div
              className={`card border-2 ${
                analysisResult.recommendation.better_option === 'salary'
                  ? 'border-green-500'
                  : 'border-transparent'
              }`}
            >
              {analysisResult.recommendation.better_option === 'salary' && (
                <div className="flex items-center gap-2 text-green-600 mb-3">
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-sm font-medium">Doporučeno</span>
                </div>
              )}
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                💼 Mzda / DPP
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-500">Čistá částka</span>
                  <span className="font-bold text-gray-900">
                    {formatCurrency(analysisResult.salary.net_amount)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Celková daň</span>
                  <span className="text-gray-700">
                    {formatCurrency(analysisResult.salary.total_tax)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Efektivní sazba</span>
                  <span className="text-gray-700">
                    {formatPercent(analysisResult.salary.effective_rate * 100)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Náklady zaměstnavatele</span>
                  <span className="text-gray-700">
                    {formatCurrency(analysisResult.salary.employer_cost)}
                  </span>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-gray-200 text-xs text-gray-500">
                <p>15% DPFO + sociální a zdravotní pojištění</p>
              </div>
            </div>
          </div>

          {/* Recommendation */}
          <div className="card bg-green-50 border-green-200">
            <div className="flex items-start gap-3">
              <Calculator className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-semibold text-green-800">
                  Doporučení
                </h3>
                <p className="text-green-700 mt-1">
                  {analysisResult.recommendation.reasoning}
                </p>
                <p className="text-green-800 font-bold mt-2">
                  Potenciální úspora:{' '}
                  {formatCurrency(analysisResult.recommendation.savings)}
                </p>
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="flex items-start gap-2 text-sm text-gray-500">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <p>
              Výpočty jsou orientační a nezohledňují všechny individuální
              okolnosti. Pro závazné daňové plánování konzultujte s daňovým
              poradcem.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
