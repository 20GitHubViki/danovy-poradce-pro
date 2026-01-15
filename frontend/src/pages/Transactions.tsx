import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search, Filter } from 'lucide-react'
import { api } from '@/services/api'
import { formatCurrency, formatDate } from '@/utils/formatters'

type Transaction = {
  id: number
  type: string
  category: string
  amount_czk: number
  date: string
  description: string
}

export default function Transactions() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['transactions', 1],
    queryFn: () => api.get('/transactions?company_id=1'),
  })

  // Mock data for demo
  const mockTransactions: Transaction[] = [
    {
      id: 1,
      type: 'income',
      category: 'App Store',
      amount_czk: 45000,
      date: '2026-01-15',
      description: 'Příjem z App Store - leden',
    },
    {
      id: 2,
      type: 'expense',
      category: 'Software',
      amount_czk: 2500,
      date: '2026-01-14',
      description: 'Předplatné GitHub Pro',
    },
    {
      id: 3,
      type: 'expense',
      category: 'Hardware',
      amount_czk: 35000,
      date: '2026-01-10',
      description: 'MacBook Pro - odpis 1/3',
    },
    {
      id: 4,
      type: 'income',
      category: 'App Store',
      amount_czk: 52000,
      date: '2026-01-01',
      description: 'Příjem z App Store - prosinec',
    },
  ]

  const transactions = data?.items || mockTransactions

  const filteredTransactions = transactions.filter((t: Transaction) => {
    const matchesSearch =
      t.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.category.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesFilter = !filterType || t.type === filterType
    return matchesSearch && matchesFilter
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transakce</h1>
          <p className="text-gray-500">Správa příjmů a výdajů</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Nová transakce
        </button>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Hledat transakce..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input w-full pl-10"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setFilterType(null)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterType === null
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Vše
            </button>
            <button
              onClick={() => setFilterType('income')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterType === 'income'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Příjmy
            </button>
            <button
              onClick={() => setFilterType('expense')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterType === 'expense'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Výdaje
            </button>
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="card overflow-hidden p-0">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Datum
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Popis
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Kategorie
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Částka
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                  Načítám transakce...
                </td>
              </tr>
            ) : filteredTransactions.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                  Žádné transakce nenalezeny
                </td>
              </tr>
            ) : (
              filteredTransactions.map((transaction: Transaction) => (
                <tr
                  key={transaction.id}
                  className="hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(transaction.date)}
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm font-medium text-gray-900">
                      {transaction.description}
                    </p>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700">
                      {transaction.category}
                    </span>
                  </td>
                  <td
                    className={`px-6 py-4 whitespace-nowrap text-sm font-medium text-right ${
                      transaction.type === 'income'
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}
                  >
                    {transaction.type === 'income' ? '+' : '-'}
                    {formatCurrency(transaction.amount_czk)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
