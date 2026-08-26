from fastapi import APIRouter
from backend.app.models.guardrail import GuardrailConfig
from backend.app.guardrails.policy_engine import policy_engine

router = APIRouter(prefix="/guardrails", tags=["Deterministic Guardrails & Policy Engine"])

@router.get("/config", response_model=GuardrailConfig)
def get_guardrail_config():
    return policy_engine.config

@router.post("/config", response_model=GuardrailConfig)
def update_guardrail_config(config: GuardrailConfig):
    policy_engine.update_config(config)
    return policy_engine.config
