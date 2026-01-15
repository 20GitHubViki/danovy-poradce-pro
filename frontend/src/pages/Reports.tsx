import { FileText, Download } from 'lucide-react'

export default function Reports() {
  const reports = [
    {
      name: 'Výsledovka (P&L)',
      description: 'Přehled příjmů a výdajů za období',
      available: true,
    },
    {
      name: 'Rozvaha',
      description: 'Aktiva a pasiva společnosti',
      available: false,
    },
    {
      name: 'Cash Flow',
      description: 'Přehled peněžních toků',
      available: true,
    },
    {
      name: 'Daňová projekce',
      description: 'Odhad daňové povinnosti na konec roku',
      available: true,
    },
    {
      name: 'Přehled dividend',
      description: 'Historie vyplacených dividend',
      available: false,
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reporty</h1>
        <p className="text-gray-500">Finanční přehledy a výkazy</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reports.map((report) => (
          <div key={report.name} className="card">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <FileText className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <h3 className="font-medium text-gray-900">{report.name}</h3>
                  <p className="text-sm text-gray-500">{report.description}</p>
                </div>
              </div>
              {report.available ? (
                <button className="btn-secondary flex items-center gap-2 text-sm">
                  <Download className="w-4 h-4" />
                  Stáhnout
                </button>
              ) : (
                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                  Brzy
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
