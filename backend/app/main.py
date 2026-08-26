import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database.db import init_db
from backend.app.api.chat import router as chat_router
from backend.app.api.acp import router as acp_router
from backend.app.api.merchant import router as merchant_router
from backend.app.api.guardrails import router as guardrails_router
from backend.app.api.webhooks import router as webhooks_router
from backend.app.api.audit import router as audit_router
from backend.app.api.scenarios import router as scenarios_router
from backend.app.api.payments import router as payments_router
from backend.app.api.products import router as products_router
from backend.app.api.cart import router as cart_router
from backend.app.api.checkout import router as checkout_router
from backend.app.api.approve import router as approve_router
from backend.app.api.orders import router as orders_router
from backend.app.api.refunds import router as refunds_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema and seed catalog on startup
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="pay-pipeline - Autonomous Agentic Commerce, Revenue Growth & Deterministic Policy Platform",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all core API routers
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(products_router, prefix=settings.API_V1_STR)
app.include_router(cart_router, prefix=settings.API_V1_STR)
app.include_router(checkout_router, prefix=settings.API_V1_STR)
app.include_router(approve_router, prefix=settings.API_V1_STR)
app.include_router(orders_router, prefix=settings.API_V1_STR)
app.include_router(refunds_router, prefix=settings.API_V1_STR)
app.include_router(payments_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)
app.include_router(acp_router, prefix=settings.API_V1_STR)
app.include_router(merchant_router, prefix=settings.API_V1_STR)
app.include_router(guardrails_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(scenarios_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "system": settings.PROJECT_NAME,
        "payment_mode": settings.PAYMENT_PROVIDER_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "database": "sqlite",
    }


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
