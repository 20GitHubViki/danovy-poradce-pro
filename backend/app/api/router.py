"""
Main API router aggregating all route modules.
"""

from fastapi import APIRouter

from app.api.v1 import transactions, invoices, companies, reports, tax, ai, memory, appstore, exchange, ocr, assets, system, auth, knowledge, osvc

api_router = APIRouter()

# Auth routes (no prefix for cleaner URLs)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# Knowledge base routes
api_router.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["Knowledge Base"],
)

# OSVČ routes
api_router.include_router(
    osvc.router,
    prefix="/osvc",
    tags=["OSVČ"],
)

# Include all route modules
api_router.include_router(
    companies.router,
    prefix="/companies",
    tags=["Companies"],
)
api_router.include_router(
    transactions.router,
    prefix="/transactions",
    tags=["Transactions"],
)
api_router.include_router(
    invoices.router,
    prefix="/invoices",
    tags=["Invoices"],
)
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
)
api_router.include_router(
    tax.router,
    prefix="/tax",
    tags=["Tax"],
)
api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI"],
)
api_router.include_router(
    memory.router,
    prefix="/memory",
    tags=["Memory"],
)
api_router.include_router(
    appstore.router,
    prefix="/appstore",
    tags=["App Store"],
)
api_router.include_router(
    exchange.router,
    prefix="/exchange",
    tags=["Exchange Rates"],
)
api_router.include_router(
    ocr.router,
    prefix="/ocr",
    tags=["OCR"],
)
api_router.include_router(
    assets.router,
    prefix="/assets",
    tags=["Assets"],
)
api_router.include_router(
    system.router,
    prefix="/system",
    tags=["System"],
)
