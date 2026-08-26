from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.api.chat import router as chat_router
from backend.app.api.acp import router as acp_router
from backend.app.api.merchant import router as merchant_router
from backend.app.api.guardrails import router as guardrails_router
from backend.app.api.webhooks import router as webhooks_router
from backend.app.api.audit import router as audit_router
from backend.app.api.scenarios import router as scenarios_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Enterprise Multi-Agent Commerce Engine with Deterministic Guardrails, Razorpay Test Rails, and ACP Machine Storefront."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(acp_router, prefix=settings.API_V1_STR)
app.include_router(merchant_router, prefix=settings.API_V1_STR)
app.include_router(guardrails_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(scenarios_router, prefix=settings.API_V1_STR)

@app.get("/health")
def healthcheck():
    return {
        "status": "HEALTHY",
        "system": settings.PROJECT_NAME,
        "environment": "Razorpay Test-Mode / ACP Ready",
        "guardrail_status": "DETERMINISTIC_ACTIVE"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
