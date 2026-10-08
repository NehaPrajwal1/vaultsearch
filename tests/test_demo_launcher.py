"""Operator launcher checks; no model or server is started."""
import socket
from pathlib import Path
import pytest
from run_demo import prepare, ROOT


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return sock.getsockname()[1]


def test_persona_alias_and_fresh_tokens():
    user, first = prepare("dmitri", free_port())
    other, second = prepare("user:dmitri", free_port())
    assert user == other == "user:dmitri"
    assert len(first) >= 32 and len(second) >= 32 and first != second


def test_unknown_persona_fails_before_launch():
    with pytest.raises(ValueError, match="Unknown demo identity"):
        prepare("not-a-user", free_port())


def test_occupied_port_does_not_replace_existing_listener():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",0)); listener.listen()
        port=listener.getsockname()[1]
        with pytest.raises(ValueError, match="No server was stopped"):
            prepare("ines",port)
        assert listener.getsockname()[1] == port


def test_missing_corpus_reports_setup_step(tmp_path):
    (tmp_path/"data").mkdir()
    (tmp_path/"data/users_groups.json").write_bytes((ROOT/"data/users_groups.json").read_bytes())
    with pytest.raises(ValueError,match="ingestion/ingest.py"):
        prepare("ines",free_port(),tmp_path)
