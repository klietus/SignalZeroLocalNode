import os
import json
from pathlib import Path
from typing import List, Tuple

class ChatHistory:
    def __init__(self, storage_dir="chat_sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.jsonl"

    def append_message(self, session_id: str, role: str, content: str):
        record = {"role": role, "content": content}
        with self._session_file(session_id).open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def get_history(self, session_id: str) -> List[Tuple[str, str]]:
        path = self._session_file(session_id)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            return [(json.loads(line)["role"], json.loads(line)["content"]) for line in f if line.strip()]

    def clear_history(self, session_id: str):
        path = self._session_file(session_id)
        if path.exists():
            path.unlink()

    def list_sessions(self) -> List[str]:
        return [p.stem for p in self.storage_dir.glob("*.jsonl")]
