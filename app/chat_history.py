import json
from pathlib import Path
from typing import List, Tuple

from app.encryption import EncryptionError, get_cipher

class ChatHistory:
    def __init__(self, storage_dir: str = "chat_sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._cipher = get_cipher()

    def _session_file(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.jsonl"

    def append_message(self, session_id: str, role: str, content: str) -> None:
        record = {"role": role, "content": content}
        payload = json.dumps(record).encode("utf-8")
        encrypted = self._cipher.encrypt(payload)
        with self._session_file(session_id).open("a", encoding="utf-8") as f:
            f.write(encrypted + "\n")

    def get_history(self, session_id: str) -> List[Tuple[str, str]]:
        path = self._session_file(session_id)
        if not path.exists():
            log.debug("chat_history.fetch_empty", session_id=session_id)
            return []
        turns: List[Tuple[str, str]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    decrypted = self._cipher.decrypt(line)
                except EncryptionError as exc:  # pragma: no cover - defensive guard
                    raise ValueError(
                        "Failed to decrypt chat history. The encryption key may be invalid."
                    ) from exc
                record = json.loads(decrypted.decode("utf-8"))
                turns.append((record["role"], record["content"]))
        return turns

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
