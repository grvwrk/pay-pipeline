from backend.app.models.order import TransactionState

class TransactionStateMachine:
    VALID_TRANSITIONS = {
        TransactionState.DISCOVERED: [TransactionState.SELECTED, TransactionState.DENIED],
        TransactionState.SELECTED: [TransactionState.CART_CREATED, TransactionState.DISCOVERED],
        TransactionState.CART_CREATED: [TransactionState.GUARDRAIL_EVALUATED, TransactionState.DISCOVERED],
        TransactionState.GUARDRAIL_EVALUATED: [
            TransactionState.PENDING_APPROVAL,
            TransactionState.ORDER_CREATED,
            TransactionState.DENIED
        ],
        TransactionState.PENDING_APPROVAL: [TransactionState.ORDER_CREATED, TransactionState.DENIED],
        TransactionState.ORDER_CREATED: [TransactionState.PAYMENT_PENDING, TransactionState.DENIED],
        TransactionState.PAYMENT_PENDING: [TransactionState.PAYMENT_CAPTURED, TransactionState.PAYMENT_FAILED],
        TransactionState.PAYMENT_CAPTURED: [TransactionState.COMPLETED, TransactionState.REFUNDED],
        TransactionState.PAYMENT_FAILED: [TransactionState.PAYMENT_PENDING, TransactionState.DENIED],
        TransactionState.COMPLETED: [TransactionState.REFUNDED],
        TransactionState.REFUNDED: [],
        TransactionState.DENIED: []
    }

    @classmethod
    def can_transition(cls, current: TransactionState, target: TransactionState) -> bool:
        return target in cls.VALID_TRANSITIONS.get(current, [])

    @classmethod
    def transition(cls, current: TransactionState, target: TransactionState) -> TransactionState:
        if not cls.can_transition(current, target):
            raise ValueError(f"Illegal state transition from {current} to {target}")
        return target

state_machine = TransactionStateMachine()
