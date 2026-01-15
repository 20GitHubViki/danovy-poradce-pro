import { useState } from 'react'
import { Building2, User, Bot, Database } from 'lucide-react'

export default function Settings() {
  const [activeTab, setActiveTab] = useState('company')

  const tabs = [
    { id: 'company', name: 'Společnost', icon: Building2 },
    { id: 'person', name: 'Osobní údaje', icon: User },
    { id: 'ai', name: 'AI nastavení', icon: Bot },
    { id: 'data', name: 'Data', icon: Database },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Nastavení</h1>
        <p className="text-gray-500">Konfigurace aplikace</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.name}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="card">
        {activeTab === 'company' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Údaje o společnosti
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Název společnosti</label>
                <input
                  type="text"
                  className="input w-full"
                  defaultValue="Moje Firma s.r.o."
                />
              </div>
              <div>
                <label className="label">IČO</label>
                <input
                  type="text"
                  className="input w-full"
                  defaultValue="12345678"
                />
              </div>
              <div>
                <label className="label">DIČ</label>
                <input
                  type="text"
                  className="input w-full"
                  defaultValue="CZ12345678"
                />
              </div>
              <div>
                <label className="label">Bankovní účet</label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="123456789/0100"
                />
              </div>
              <div className="md:col-span-2">
                <label className="label">Adresa sídla</label>
                <textarea
                  className="input w-full"
                  rows={2}
                  defaultValue="Václavské náměstí 1, 110 00 Praha 1"
                />
              </div>
            </div>
            <button className="btn-primary">Uložit změny</button>
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Nastavení AI agenta
            </h2>
            <div>
              <label className="label">API klíč (Anthropic)</label>
              <input
                type="password"
                className="input w-full"
                placeholder="sk-ant-..."
              />
              <p className="text-xs text-gray-500 mt-1">
                Klíč je bezpečně uložen lokálně
              </p>
            </div>
            <div>
              <label className="label">Model</label>
              <select className="input w-full">
                <option value="claude-sonnet-4-20250514">Claude Sonnet 4.5</option>
                <option value="claude-opus-4-5-20250929">Claude Opus 4.5</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="autoConfirm" className="rounded" />
              <label htmlFor="autoConfirm" className="text-sm text-gray-700">
                Automaticky potvrzovat doporučení AI
              </label>
            </div>
            <button className="btn-primary">Uložit nastavení</button>
          </div>
        )}

        {activeTab === 'person' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Osobní údaje pro daňové přiznání FO
            </h2>
            <p className="text-gray-500">
              Tyto údaje se použijí pro výpočet daně z příjmu fyzických osob.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Jméno a příjmení</label>
                <input type="text" className="input w-full" />
              </div>
              <div>
                <label className="label">Počet vyživovaných dětí</label>
                <input type="number" className="input w-full" defaultValue="0" />
              </div>
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" defaultChecked />
                <span className="text-sm text-gray-700">
                  Sleva na poplatníka (30 840 Kč)
                </span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" />
                <span className="text-sm text-gray-700">
                  Sleva na manžela/manželku
                </span>
              </label>
            </div>
            <button className="btn-primary">Uložit údaje</button>
          </div>
        )}

        {activeTab === 'data' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Správa dat
            </h2>
            <div className="space-y-3">
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium text-gray-900">Export dat</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Stáhněte všechna data ve formátu JSON
                </p>
                <button className="btn-secondary mt-2">Exportovat</button>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium text-gray-900">Import dat</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Nahrajte data z předchozího exportu
                </p>
                <button className="btn-secondary mt-2">Importovat</button>
              </div>
              <div className="p-4 bg-red-50 rounded-lg">
                <h3 className="font-medium text-red-900">Smazat všechna data</h3>
                <p className="text-sm text-red-700 mt-1">
                  Tato akce je nevratná!
                </p>
                <button className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors mt-2">
                  Smazat vše
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
