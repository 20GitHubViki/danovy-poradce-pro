# Daňový Poradce Pro - Backend

AI-powered tax and accounting platform for Czech s.r.o. and individuals.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```
