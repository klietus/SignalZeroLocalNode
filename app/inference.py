# app/inference.py

from app import embedding_index, chat_history
from app.symbol_store import get_symbol
from app.prompt_generator import build_prompt
from app.model_call import model_call


def run_query(user_query: str, session_id: str, k: int = 5) -> Dict:
    nearest = embedding_index.search(user_query, k)

    context_symbols = []
    for sid, _ in nearest:
        symbol = get_symbol(sid)
        if symbol:
            context_symbols.append(symbol)

    # Load recent chat history
    chat_turns = chat_history.get_history(session_id)

    # Append new user message (we add model response after inference)
    chat_history.append_message(session_id, "user", user_query)

    # Generate prompt
    prompt = build_prompt(user_query, context_symbols, chat_turns)

    reply_text = model_call(prompt)
    chat_history.append_message(session_id, "assistant", reply_text)

    return {
        "reply": reply_text,
        "symbols_used": [s.id for s in context_symbols],
        "history_length": len(chat_turns)
    }
