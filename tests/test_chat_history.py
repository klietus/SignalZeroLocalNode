from app.chat_history import ChatHistory


def test_chat_history_persistence(tmp_path):
    storage = tmp_path / "history"
    history = ChatHistory(storage_dir=storage)

    history.append_message("session1", "user", "hello")
    history.append_message("session1", "assistant", "hi there")

    turns = history.get_history("session1")
    assert turns == [("user", "hello"), ("assistant", "hi there")]

    sessions = history.list_sessions()
    assert sessions == ["session1"]

    history.clear_history("session1")
    assert history.get_history("session1") == []


def test_chat_history_encrypted_on_disk(tmp_path):
    storage = tmp_path / "history"
    history = ChatHistory(storage_dir=storage)

    history.append_message("secret-session", "user", "super secret message")

    session_file = storage / "secret-session.jsonl"
    raw_content = session_file.read_text(encoding="utf-8")

    assert "super secret message" not in raw_content
    assert raw_content.strip().startswith("{") is False

    turns = history.get_history("secret-session")
    assert turns == [("user", "super secret message")]
