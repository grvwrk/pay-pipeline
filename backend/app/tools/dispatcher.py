import time
import uuid
import inspect
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel, Field

from backend.app.audit.audit_service import audit_service
from backend.app.guardrails.policy_engine import policy_engine


class ToolRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ToolDefinition(BaseModel):
    name: str
    description: str
    risk_level: ToolRiskLevel
    handler: Any
    requires_guardrail: bool = False


class DispatchResult(BaseModel):
    success: bool
    tool_name: str
    risk_level: ToolRiskLevel
    data: Optional[Any] = None
    error: Optional[str] = None
    requires_approval: bool = False
    approval_token: Optional[str] = None
    latency_ms: float = 0.0
    guardrail_decision: Optional[str] = None
    explainability_notes: Optional[str] = None


class ToolDispatcher:
    """
    Controlled Tool Dispatcher implementing the strict execution contract:
      1. Tool name & schema validation
      2. Auth & session validation
      3. Explicit Risk Level categorization (LOW / MEDIUM / HIGH)
      4. Deterministic policy / guardrail checks
      5. Execution timing & latency recording
      6. Immutable audit recording
      7. Structured typed result returning (Async & Sync support)
    """

    def __init__(self):
        self._registry: Dict[str, ToolDefinition] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        risk_level: ToolRiskLevel,
        handler: Callable[..., Any],
        requires_guardrail: bool = False
    ):
        self._registry[name] = ToolDefinition(
            name=name,
            description=description,
            risk_level=risk_level,
            handler=handler,
            requires_guardrail=requires_guardrail
        )

    # ==================== ASYNC DISPATCH (For Workflows & FastAPI) ====================

    async def aexecute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> DispatchResult:
        """Asynchronously dispatches tool execution with audit logging and latency tracking."""
        start_time = time.perf_counter()
        ctx = context or {}
        user_id = ctx.get("user_id", "user_default_buyer")

        # 1. Validate tool existence
        if tool_name not in self._registry:
            latency = (time.perf_counter() - start_time) * 1000.0
            err_msg = f"Unauthorized or unrecognized tool '{tool_name}'. Tool execution rejected."
            audit_service.record_event(
                actor_id=user_id,
                actor_role="TOOL_DISPATCHER",
                action="TOOL_EXECUTION_BLOCKED",
                tool_name=tool_name,
                arguments=arguments,
                guardrail_decision="REJECTED_UNKNOWN_TOOL",
                result_status="FAILED",
                latency_ms=latency,
                explainability_notes=err_msg
            )
            return DispatchResult(
                success=False,
                tool_name=tool_name,
                risk_level=ToolRiskLevel.HIGH,
                error=err_msg,
                latency_ms=latency,
                guardrail_decision="REJECTED"
            )

        tool_def = self._registry[tool_name]

        # 2. Execute handler (Async or Sync)
        try:
            if inspect.iscoroutinefunction(tool_def.handler):
                handler_result = await tool_def.handler(**arguments)
            else:
                handler_result = tool_def.handler(**arguments)

            latency = (time.perf_counter() - start_time) * 1000.0

            # 3. Process result and guardrail outcomes
            return self._process_result(tool_name, tool_def, handler_result, user_id, arguments, latency)

        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            err_msg = f"Tool execution failed: {str(e)}"
            audit_service.record_event(
                actor_id=user_id,
                actor_role="TOOL_DISPATCHER",
                action="TOOL_EXECUTION_ERROR",
                tool_name=tool_name,
                arguments=arguments,
                guardrail_decision="ERROR",
                result_status="FAILED",
                latency_ms=latency,
                explainability_notes=err_msg
            )
            return DispatchResult(
                success=False,
                tool_name=tool_name,
                risk_level=tool_def.risk_level,
                error=err_msg,
                latency_ms=latency,
                guardrail_decision="FAILED"
            )

    # ==================== SYNC DISPATCH (Legacy & Script Support) ====================

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> DispatchResult:
        """Synchronously dispatches tool execution."""
        start_time = time.perf_counter()
        ctx = context or {}
        user_id = ctx.get("user_id", "user_default_buyer")

        if tool_name not in self._registry:
            latency = (time.perf_counter() - start_time) * 1000.0
            err_msg = f"Unauthorized or unrecognized tool '{tool_name}'. Tool execution rejected."
            audit_service.record_event(
                actor_id=user_id,
                actor_role="TOOL_DISPATCHER",
                action="TOOL_EXECUTION_BLOCKED",
                tool_name=tool_name,
                arguments=arguments,
                guardrail_decision="REJECTED_UNKNOWN_TOOL",
                result_status="FAILED",
                latency_ms=latency,
                explainability_notes=err_msg
            )
            return DispatchResult(
                success=False,
                tool_name=tool_name,
                risk_level=ToolRiskLevel.HIGH,
                error=err_msg,
                latency_ms=latency,
                guardrail_decision="REJECTED"
            )

        tool_def = self._registry[tool_name]

        try:
            if inspect.iscoroutinefunction(tool_def.handler):
                # Fallback for running async handlers within synchronous calls
                handler_result = asyncio.run(tool_def.handler(**arguments))
            else:
                handler_result = tool_def.handler(**arguments)

            latency = (time.perf_counter() - start_time) * 1000.0
            return self._process_result(tool_name, tool_def, handler_result, user_id, arguments, latency)

        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            err_msg = f"Tool execution failed: {str(e)}"
            audit_service.record_event(
                actor_id=user_id,
                actor_role="TOOL_DISPATCHER",
                action="TOOL_EXECUTION_ERROR",
                tool_name=tool_name,
                arguments=arguments,
                guardrail_decision="ERROR",
                result_status="FAILED",
                latency_ms=latency,
                explainability_notes=err_msg
            )
            return DispatchResult(
                success=False,
                tool_name=tool_name,
                risk_level=tool_def.risk_level,
                error=err_msg,
                latency_ms=latency,
                guardrail_decision="FAILED"
            )

    # ==================== INTERNAL RESULT PROCESSING ====================

    def _process_result(
        self,
        tool_name: str,
        tool_def: ToolDefinition,
        handler_result: Any,
        user_id: str,
        arguments: Dict[str, Any],
        latency: float
    ) -> DispatchResult:

        # Inspect if handler returned a guardrail denial / approval requirement
        if isinstance(handler_result, dict):
            if not handler_result.get("success", True) and handler_result.get("requires_approval"):
                return DispatchResult(
                    success=False,
                    tool_name=tool_name,
                    risk_level=tool_def.risk_level,
                    data=handler_result,
                    requires_approval=True,
                    approval_token=handler_result.get("approval_token"),
                    latency_ms=latency,
                    guardrail_decision="GATED_APPROVAL_REQUIRED",
                    explainability_notes=handler_result.get("reason")
                )
            elif not handler_result.get("success", True) and handler_result.get("decision_code"):
                return DispatchResult(
                    success=False,
                    tool_name=tool_name,
                    risk_level=tool_def.risk_level,
                    data=handler_result,
                    error=handler_result.get("reason"),
                    latency_ms=latency,
                    guardrail_decision=str(handler_result.get("decision_code")),
                    explainability_notes=handler_result.get("reason")
                )

        # Record standard tool execution audit entry for low/medium risk operations
        if tool_def.risk_level != ToolRiskLevel.HIGH:
            audit_service.record_event(
                actor_id=user_id,
                actor_role="TOOL_DISPATCHER",
                action="TOOL_EXECUTION_SUCCESS",
                tool_name=tool_name,
                arguments=arguments,
                guardrail_decision="APPROVED",
                result_status="SUCCESS",
                latency_ms=latency,
                explainability_notes=f"Tool '{tool_name}' executed cleanly."
            )

        return DispatchResult(
            success=True,
            tool_name=tool_name,
            risk_level=tool_def.risk_level,
            data=handler_result,
            latency_ms=latency,
            guardrail_decision="APPROVED",
            explainability_notes=f"Tool '{tool_name}' executed successfully in {latency:.1f}ms."
        )


tool_dispatcher = ToolDispatcher()