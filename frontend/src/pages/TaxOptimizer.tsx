import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Calculator, TrendingUp, AlertCircle, Bot, Loader2 } from 'lucide-react'
import { api } from '@/services/api'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import { useSettingsStore } from '@/stores'

interface DividendVsSalaryResult {
  recommendation: string
  dividend_net: number
  salary_net: number
  savings: number
  explanation: string
  legal_references: string[]
  warnings: string[]
}

export default function TaxOptimizer() {
  const [profit, setProfit] = useState('')
  const [otherIncome, setOtherIncome] = useState('')
  const { aiStatus, fetchAIStatus } = useSettingsStore()

  // Fetch AI status on mount
  useQuery({
    queryKey: ['ai-status'],
    queryFn: async () => {
      await fetchAIStatus()
      return true
    },
  })

  const { mutate: analyze, data: result, isPending, error } = useMutation({
    mutationFn: (params: { available_profit: number; other_income: number }) =>
      api.post<DividendVsSalaryResult>('/ai/dividend-vs-salary', params),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const profitValue = parseFloat(profit)
    if (profitValue > 0) {
      analyze({
        available_profit: profitValue,
        other_income: parseFloat(otherIncome) || 0,
      })
    }
  }

  // Calculate display values from result
  const analysisResult = result ? {
    dividend: {
      net_amount: Number(result.dividend_net),
      total_tax: parseFloat(profit) - Number(result.dividend_net),
      effective_rate: (parseFloat(profit) - Number(result.dividend_net)) / parseFloat(profit),
    },
    salary: {
      net_amount: Number(result.salary_net),
      total_tax: parseFloat(profit) - Number(result.salary_net),
      effective_rate: (parseFloat(profit) - Number(result.salary_net)) / parseFloat(profit),
      employer_cost: parseFloat(profit), // Simplified
    },
    recommendation: {
      better_option: result.recommendation,
      savings: Number(result.savings),
      reasoning: result.explanation,
    },
    legal_references: result.legal_references,
    warnings: result.warnings,
  } : null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daňový optimalizátor</h1>
          <p className="text-gray-500">
            Porovnání variant výplaty zisku: dividenda vs. mzda
          </p>
        </div>
        {aiStatus?.configured && (
          <div className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
            <Bot className="w-4 h-4" />
            AI aktivní
          </div>
        )}
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
                  min="1"
                  className="input w-full pr-12"
                  required
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
                  min="0"
                  className="input w-full pr-12"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  Kč
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Pro výpočet solidární daně (nad ~2M Kč ročně)
              </p>
            </div>
          </div>
          <button
            type="submit"
            disabled={isPending || !profit}
            className="btn-primary flex items-center gap-2"
          >
            {isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzuji...
              </>
            ) : (
              <>
                <Calculator className="w-4 h-4" />
                Analyzovat
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-red-50 border-red-200">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle className="w-5 h-5" />
            <p>Chyba při analýze: {error instanceof Error ? error.message : 'Neznámá chyba'}</p>
          </div>
        </div>
      )}

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
                Dividenda
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
                Mzda / DPP
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-500">Čistá částka</span>
                  <span className="font-bold text-gray-900">
                    {formatCurrency(analysisResult.salary.net_amount)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Celková daň + odvody</span>
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
                <p className="text-green-700 mt-1 whitespace-pre-line">
                  {analysisResult.recommendation.reasoning}
                </p>
                <p className="text-green-800 font-bold mt-2">
                  Potenciální úspora:{' '}
                  {formatCurrency(analysisResult.recommendation.savings)}
                </p>
              </div>
            </div>
          </div>

          {/* Legal References */}
          {analysisResult.legal_references && analysisResult.legal_references.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-2">Právní reference</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                {analysisResult.legal_references.map((ref, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-gray-400">•</span>
                    {ref}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {analysisResult.warnings && analysisResult.warnings.length > 0 && (
            <div className="flex items-start gap-2 text-sm text-gray-500">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                {analysisResult.warnings.map((warning, i) => (
                  <p key={i}>{warning}</p>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Info when no result */}
      {!result && !isPending && (
        <div className="card bg-blue-50 border-blue-200">
          <div className="flex items-start gap-3">
            <Bot className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
            <div>
              <h3 className="text-lg font-semibold text-blue-800">
                Jak to funguje?
              </h3>
              <ul className="text-blue-700 mt-2 space-y-1 text-sm">
                <li>1. Zadejte zisk vaší s.r.o. před zdaněním</li>
                <li>2. Volitelně zadejte ostatní příjmy (ze zaměstnání)</li>
                <li>3. Systém vypočítá a porovná obě varianty výplaty</li>
                <li>4. Doporučí optimální strategii s konkrétní úsporou</li>
              </ul>
              {aiStatus?.configured && (
                <p className="text-blue-600 mt-3 text-sm">
                  S aktivní AI získáte detailní vysvětlení s právními referencemi.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
