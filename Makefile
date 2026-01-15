.PHONY: help install install-dev dev backend frontend build test lint format clean

# Default target
help:
	@echo "Daňový Poradce Pro - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install all dependencies"
	@echo "  make install-dev  Install with dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev          Start both backend and frontend"
	@echo "  make backend      Start only backend"
	@echo "  make frontend     Start only frontend"
	@echo ""
	@echo "Build & Test:"
	@echo "  make build        Build for production"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run linters"
	@echo "  make format       Format code"
	@echo ""
	@echo "Other:"
	@echo "  make clean        Clean build artifacts"
	@echo "  make init-db      Initialize database"

# Installation
install:
	cd backend && pip install -e .
	cd frontend && npm install

install-dev:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# Development
dev:
	@echo "Starting development servers..."
	@make -j2 backend frontend

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# Build
build:
	cd frontend && npm run build
	@mkdir -p backend/app/static
	cp -r frontend/dist/* backend/app/static/

# Testing
test:
	cd backend && pytest
	cd frontend && npm run type-check

test-backend:
	cd backend && pytest -v --cov=app

test-frontend:
	cd frontend && npm run type-check

# Linting
lint:
	cd backend && ruff check . && mypy app
	cd frontend && npm run lint

lint-fix:
	cd backend && ruff check . --fix
	cd frontend && npm run lint:fix

# Formatting
format:
	cd backend && black . && ruff check . --fix
	cd frontend && npm run format

# Database
init-db:
	cd backend && python -c "from app.database import init_db; init_db()"

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/app/static 2>/dev/null || true

# Memory system
memory-export:
	@python -c "import asyncio; from app.memory import MemoryManager; m = MemoryManager(); asyncio.run(m.export_memory('memory_backup.json'))"
	@echo "Memory exported to memory_backup.json"

memory-status:
	@python -c "import asyncio; from app.memory import MemoryManager; m = MemoryManager(); print(asyncio.run(m.generate_project_summary()))"
