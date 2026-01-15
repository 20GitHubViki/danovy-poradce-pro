import { Plus } from 'lucide-react'

export default function Invoices() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Faktury</h1>
          <p className="text-gray-500">Správa vydaných a přijatých faktur</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Nová faktura
        </button>
      </div>

      <div className="card">
        <p className="text-gray-500 text-center py-8">
          Modul faktur bude brzy dostupný.
        </p>
      </div>
    </div>
  )
}
