"""Tests for JWT security configuration and token validation helpers."""
from __future__ import annotations

import importlib

import pytest

import pgis_bodyweight.api.security as security


def _reload_security(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    return importlib.reload(security)


def test_local_development_allows_fallback_secret(monkeypatch):
    module = _reload_security(monkeypatch)
    assert module._resolve_jwt_secret() == "dev-secret-change-in-prod"


def test_environment_production_requires_jwt_secret(monkeypatch):
    _reload_security(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="JWT_SECRET must be set"):
        importlib.reload(security)


def test_app_env_production_rejects_dev_fallback(monkeypatch):
    _reload_security(monkeypatch)
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "dev-secret-change-in-prod")
    with pytest.raises(RuntimeError, match="must not use the development fallback"):
        importlib.reload(security)


def test_railway_environment_requires_jwt_secret(monkeypatch):
    _reload_security(monkeypatch)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="JWT_SECRET must be set"):
        importlib.reload(security)


def test_production_uses_configured_secret(monkeypatch):
    _reload_security(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "real-secret-for-tests")
    module = importlib.reload(security)
    assert module._resolve_jwt_secret() == "real-secret-for-tests"
    _reload_security(monkeypatch)
