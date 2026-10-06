"""Testes do wrapper do rclone (subprocess mockado, sem rede)."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from src.drive_audit import rclone


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_rclone_retorna_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _proc(0, stdout="ok"))
    assert rclone.run_rclone(["version"]) == "ok"


def test_run_rclone_repete_em_rate_limit_e_depois_sucede(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = {"n": 0}

    def fake_run(*_a, **_k):
        chamadas["n"] += 1
        if chamadas["n"] < 3:
            return _proc(1, stderr="googleapi: Error 403: Rate Limit Exceeded, rateLimitExceeded")
        return _proc(0, stdout="[]")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert rclone.run_rclone(["lsjson"], sleep=lambda _s: None) == "[]"
    assert chamadas["n"] == 3


def test_run_rclone_erro_nao_recuperavel_falha_imediato(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = {"n": 0}

    def fake_run(*_a, **_k):
        chamadas["n"] += 1
        return _proc(1, stderr="directory not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(rclone.RcloneError):
        rclone.run_rclone(["lsjson"], sleep=lambda _s: None)
    assert chamadas["n"] == 1


def test_run_rclone_esgota_retries_em_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _proc(1, stderr="RATE_LIMIT_EXCEEDED"))
    with pytest.raises(rclone.RcloneError):
        rclone.run_rclone(["lsjson"], retries=3, sleep=lambda _s: None)


def test_lsjson_interpreta_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rclone, "run_rclone", lambda args, **kw: '[{"Path": "a", "IsDir": false}]')
    assert rclone.lsjson("gdrive:") == [{"Path": "a", "IsDir": False}]
