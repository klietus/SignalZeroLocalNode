import json
from pathlib import Path
from typing import List, Tuple

import structlog

from app.logging_config import configure_logging


configure_logging()
log = structlog.get_logger(__name__)


class ChatHistory:
    def __init__(self, storage_dir: str = "chat_sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        log.debug("chat_history.initialised", storage_dir=str(self.storage_dir))

    def _session_file(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.jsonl"

    def append_message(self, session_id: str, role: str, content: str) -> None:
        record = {"role": role, "content": content}
        path = self._session_file(session_id)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        log.info(
            "chat_history.appended",
            session_id=session_id,
            role=role,
            length=len(content),
        )

    def get_history(self, session_id: str) -> List[Tuple[str, str]]:
        path = self._session_file(session_id)
        if not path.exists():
            log.debug("chat_history.fetch_empty", session_id=session_id)
            return []
        with path.open("r", encoding="utf-8") as f:
            history = [
                (json.loads(line)["role"], json.loads(line)["content"])
                for line in f
                if line.strip()
            ]
        log.info("chat_history.fetched", session_id=session_id, count=len(history))
        return history

    def clear_history(self, session_id: str) -> None:
        path = self._session_file(session_id)
        if path.exists():
            path.unlink()
            log.info("chat_history.cleared", session_id=session_id)
        else:
            log.debug("chat_history.clear_skipped", session_id=session_id)

    def list_sessions(self) -> List[str]:
        sessions = [p.stem for p in self.storage_dir.glob("*.jsonl")]
        log.debug("chat_history.sessions_listed", count=len(sessions))
        return sessions
