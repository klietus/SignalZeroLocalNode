from scripts import count_tokens


def test_count_tokens_uses_tokenizer(capsys, monkeypatch):
    calls = {"count": 0}

    def fake_tokenizer(text: str):
        calls["count"] += 1
        return [1, 2, 3]

    monkeypatch.setattr(count_tokens, "_tokenizer", fake_tokenizer, raising=False)

    count_tokens.count_tokens("hello world")

    captured = capsys.readouterr()
    assert "Token count: 3" in captured.out
    assert calls["count"] == 1
