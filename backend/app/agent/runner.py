"""Small Responses-style tool loop for the sales agent."""

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import guard
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS, ToolContext, dispatch
from app.ai.provider import get_provider
from app.core.config import get_settings
from app.models import Message
from app.services import budget
from app.services.errors import log_error


@dataclass
class AgentReply:
    text: str
    buttons: dict | None = None
    actions: list[dict] = field(default_factory=list)

    @property
    def side_effects(self) -> list[dict]:
        return self.actions


def run_agent_turn(db: Session, conversation, user_text: str) -> AgentReply:
    settings = get_settings()
    customer = conversation.customer
    try:
        budget.check_llm(db, customer)
    except budget.BudgetExceeded:
        from app.bot.texts import AI_UNAVAILABLE

        return AgentReply(AI_UNAVAILABLE)
    history = db.scalars(
        select(Message).where(Message.conversation_id == conversation.id,
                              Message.role.in_(["user", "assistant"]))
        .order_by(Message.id.desc()).limit(settings.agent_history_turns * 2)
    ).all()
    history = list(reversed(history))
    already_saved = bool(history and history[-1].role == "user" and history[-1].content == user_text[:1000])
    input_items = [{"role": m.role, "content": m.content} for m in history]
    if not already_saved:
        input_items.append({"role": "user", "content": user_text[:1000]})
    selected = (conversation.context or {}).get("selected_product", "ninguno")
    left = max(0, settings.max_simulations_per_customer - (customer.simulations_used or 0))
    instructions = SYSTEM_PROMPT.format(selected_product=selected, simulations_left=left)
    provider = get_provider(db, customer_id=customer.id)
    ctx = ToolContext(customer, conversation)
    results: list[dict] = []
    text = ""
    calls_for_message = []
    for _ in range(settings.agent_max_tool_rounds):
        result = provider.chat(instructions, input_items, TOOLS)
        calls = [i for i in result.output_items if i.get("type") == "function_call"]
        if not calls:
            text = result.text
            break
        for call in calls:
            tool_result = dispatch(db, call["name"], call.get("arguments") or {}, ctx)
            results.append(tool_result)
            calls_for_message.append(call)
            input_items.append({"type": "function_call", **call})
            input_items.append({"type": "function_call_output", "call_id": call["call_id"],
                                "output": json.dumps(tool_result, ensure_ascii=False, separators=(",", ":"))})
    else:
        text = "No pude completar la consulta con seguridad. Usa el catálogo o intenta de nuevo."
    if not text:
        log_error(db, "agent", "max_tool_rounds", "Se excedió el máximo de rondas",
                  {"conversation_id": conversation.id}, customer_id=customer.id)
        text = "No pude completar la consulta con seguridad. Usa el catálogo o intenta de nuevo."
    _, text = guard.validate(text, results, db, customer.id)
    if not already_saved:
        db.add(Message(conversation_id=conversation.id, role="user", content=user_text[:1000]))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=text,
                   tool_calls=calls_for_message or None))
    db.commit()
    return AgentReply(text, actions=ctx.actions)
