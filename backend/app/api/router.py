"""
Main API router aggregating all route modules.
"""

from fastapi import APIRouter

from app.api.v1 import transactions, invoices, companies, reports, tax, ai, memory

api_router = APIRouter()

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
