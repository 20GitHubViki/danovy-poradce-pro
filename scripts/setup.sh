#!/bin/bash

# Daňový Poradce Pro - Setup Script
# Run this script to set up the development environment

set -e

echo "🚀 Setting up Daňový Poradce Pro..."
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ "$PYTHON_VERSION" < "3.11" ]]; then
    echo "❌ Python 3.11+ is required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# Check Node.js version
NODE_VERSION=$(node --version 2>&1 | cut -d'v' -f2 | cut -d'.' -f1)
if [[ "$NODE_VERSION" -lt 18 ]]; then
    echo "❌ Node.js 18+ is required. Found: $(node --version)"
    exit 1
fi
echo "✅ Node.js $(node --version)"

# Create virtual environment
echo ""
echo "📦 Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
echo ""
echo "📦 Installing backend dependencies..."
cd backend
pip install --upgrade pip
pip install -e ".[dev]"
cd ..

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p backend/data
mkdir -p .agent-memory

# Initialize database
echo ""
echo "🗄️ Initializing database..."
cd backend
python -c "from app.database import init_db; init_db()"
cd ..

# Create .env file if not exists
if [ ! -f backend/.env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cat > backend/.env << EOF
# Daňový Poradce Pro - Environment Variables

# Application
DEBUG=true

# Database
DATABASE_URL=sqlite:///./data/app.db

# Claude AI (optional - for AI features)
# ANTHROPIC_API_KEY=sk-ant-...

# App Store Connect (optional - for App Store integration)
# APPSTORE_KEY_ID=
# APPSTORE_ISSUER_ID=
# APPSTORE_PRIVATE_KEY_PATH=
EOF
    echo "✅ Created backend/.env - Update with your API keys"
fi

# Initialize memory system
echo ""
echo "🧠 Initializing memory system..."
python3 << 'EOF'
import json
from pathlib import Path
from datetime import datetime

memory_dir = Path(".agent-memory")
memory_dir.mkdir(exist_ok=True)

# Create initial project context
context = {
    "meta": {
        "project_name": "Daňový Poradce Pro",
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "version": "0.1.0",
        "phase": "MVP Development"
    },
    "summary": {
        "one_liner": "AI-powered daňová a účetní platforma pro s.r.o. a FO",
        "current_focus": "Initial setup completed",
        "blockers": [],
        "next_milestone": "Implement basic CRUD operations"
    },
    "architecture": {
        "backend": {
            "framework": "FastAPI",
            "language": "Python 3.11",
            "database": "SQLite"
        },
        "frontend": {
            "framework": "React 18",
            "language": "TypeScript",
            "styling": "Tailwind CSS"
        }
    },
    "file_structure": {},
    "conventions": {
        "naming": {
            "files": "snake_case for Python, PascalCase for React",
            "variables": "snake_case in Python, camelCase in TypeScript"
        }
    },
    "domain_knowledge": {
        "tax_rules": {
            "corporate_tax_2025": 0.21,
            "dividend_withholding": 0.15
        }
    },
    "active_context": {
        "current_task": None,
        "open_files": [],
        "recent_changes": ["Project initialized"],
        "pending_questions": []
    }
}

with open(memory_dir / "project_context.json", "w", encoding="utf-8") as f:
    json.dump(context, f, indent=2, ensure_ascii=False)

print("✅ Memory system initialized")
EOF

echo ""
echo "✨ Setup complete!"
echo ""
echo "To start development:"
echo "  source .venv/bin/activate"
echo "  make dev"
echo ""
echo "Or start individually:"
echo "  make backend   # Start API server on :8000"
echo "  make frontend  # Start frontend on :3000"
