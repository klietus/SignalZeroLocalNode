from datetime import datetime, timezone
from types import SimpleNamespace

from app import logging_config


def test_configure_logging_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(logging_config, "_CONFIGURED", False)
    monkeypatch.setattr(logging_config, "_ensure_log_directory", lambda: tmp_path)

    dict_configs = []

    def fake_dict_config(config):
        dict_configs.append(config)

    monkeypatch.setattr(logging_config.logging.config, "dictConfig", fake_dict_config)

    struct_calls = []

    def fake_structlog_configure(**kwargs):
        struct_calls.append(kwargs)

    monkeypatch.setattr(logging_config.structlog, "configure", fake_structlog_configure)
    captured_names = []
    monkeypatch.setattr(
        logging_config.structlog, "get_logger", lambda name: captured_names.append(name) or {"name": name}
    )

    logger_one = logging_config.get_logger("alpha")
    logger_two = logging_config.get_logger("beta")

    assert logger_one == {"name": "alpha"}
    assert logger_two == {"name": "beta"}
    assert len(dict_configs) == 1
    assert dict_configs[0]["handlers"]["file"]["filename"] == str(tmp_path / "app.log")
    assert len(struct_calls) == 1
    assert captured_names == ["alpha", "beta"]
    assert logging_config._CONFIGURED is True


def test_rotate_on_start_moves_existing_log(monkeypatch, tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("prior contents")

    fixed_now = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(logging_config, "datetime", SimpleNamespace(now=lambda tz=None: fixed_now))

    logging_config._rotate_on_start(log_file)

    assert not log_file.exists()
    rotated_files = list(tmp_path.glob("app.*.log"))
    assert len(rotated_files) == 1
    assert rotated_files[0].read_text() == "prior contents"
