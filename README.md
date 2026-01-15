# Daňový Poradce Pro 🧾

AI-powered platforma pro daňovou optimalizaci a účetnictví pro české s.r.o. a fyzické osoby.

## ✨ Funkce

- **📊 Dashboard** - Přehled příjmů, výdajů a cash flow
- **💰 Daňový optimalizátor** - Srovnání dividendy vs. mzda
- **📑 Evidence transakcí** - Příjmy a výdaje s kategorizací
- **🧾 Fakturace** - Vydané a přijaté faktury
- **🤖 AI Agent** - Doporučení založená na Claude AI
- **🧠 Memory System** - Persistentní kontext pro AI agenty

## 🚀 Rychlý start

### Požadavky

- Python 3.11+
- Node.js 18+
- Git

### Instalace

```bash
# Klonování repozitáře
git clone https://github.com/viktor/danovy-poradce-pro.git
cd danovy-poradce-pro

# Spuštění setup skriptu
./scripts/setup.sh

# Nebo manuálně:
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd ../frontend
npm install
```

### Spuštění

```bash
# Aktivace virtuálního prostředí
source .venv/bin/activate

# Spuštění obou serverů
make dev

# Nebo jednotlivě:
make backend   # API na http://localhost:8000
make frontend  # UI na http://localhost:3000
```

## 📁 Struktura projektu

```
danovy-poradce-pro/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/          # REST API endpointy
│   │   ├── models/       # SQLAlchemy modely
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logika
│   │   ├── agents/       # AI agenti (Claude)
│   │   └── memory/       # Memory system
│   ├── knowledge_base/   # Daňová znalostní báze
│   └── tests/
├── frontend/              # React frontend
│   └── src/
│       ├── components/   # UI komponenty
│       ├── pages/        # Stránky aplikace
│       ├── services/     # API komunikace
│       └── stores/       # Zustand stores
├── .agent-memory/         # Persistentní paměť AI
├── docs/                  # Dokumentace
└── scripts/               # Utility skripty
```

## 🧠 Memory System

Projekt obsahuje vestavěný Memory System pro AI agenty:

```python
from app.memory import MemoryManager

memory = MemoryManager()

# Načtení kontextu
context = await memory.load_context()

# Záznam rozhodnutí
await memory.record_decision(
    category="architecture",
    question="Jakou databázi použít?",
    decision="SQLite",
    reasoning="Lokální běh, jednoduchost"
)

# Vyhledávání
results = await memory.search("daňová optimalizace")
```

## 🔧 Konfigurace

Vytvořte `backend/.env`:

```env
# Aplikace
DEBUG=true
DATABASE_URL=sqlite:///./data/app.db

# Claude AI (volitelné)
ANTHROPIC_API_KEY=sk-ant-...

# App Store Connect (volitelné)
APPSTORE_KEY_ID=...
APPSTORE_ISSUER_ID=...
```

## 📚 API Dokumentace

Po spuštění backendu:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Hlavní endpointy

| Endpoint | Popis |
|----------|-------|
| `GET /api/v1/reports/dashboard/{id}` | Dashboard data |
| `POST /api/v1/tax/dividend-vs-salary` | Analýza výplaty |
| `GET /api/v1/transactions` | Seznam transakcí |
| `POST /api/v1/invoices` | Nová faktura |
| `GET /api/v1/memory/context` | Aktuální kontext |

## 🧪 Testování

```bash
# Všechny testy
make test

# Jen backend
make test-backend

# Jen frontend
make test-frontend
```

## 📖 Dokumentace

- [PROJECT_BRIEF.md](./PROJECT_BRIEF.md) - Projektové zadání
- [TECHNICAL_SPEC.md](./TECHNICAL_SPEC.md) - Technická specifikace
- [AGENT_FLOW.md](./AGENT_FLOW.md) - AI Agent dokumentace

## 🛠️ Vývoj

### Dostupné příkazy

```bash
make help          # Zobrazí nápovědu
make dev           # Spustí dev servery
make build         # Sestaví pro produkci
make lint          # Spustí lintery
make format        # Naformátuje kód
make test          # Spustí testy
make clean         # Vyčistí build artefakty
```

### Konvence

- **Python**: Black formatter, Ruff linter
- **TypeScript**: Prettier, ESLint
- **Git**: Conventional commits

## 📄 Licence

MIT License - viz [LICENSE](./LICENSE)

## 👤 Autor

Viktor ([@viktor](https://github.com/viktor))

---

*Vytvořeno s pomocí Claude AI* 🤖
