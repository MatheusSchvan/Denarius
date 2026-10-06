"""Verifica o comportamento do modo online sem usar uma conta externa."""
import asyncio

import httpx
import pytest

from app.main import app, lifespan


def test_demo_requires_password_and_is_seeded_with_fictitious_data(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCEIRO_DEMO_MODE", "1")
    monkeypatch.setenv("FINANCEIRO_DEMO_USER", "demo")
    monkeypatch.setenv("FINANCEIRO_DEMO_PASSWORD", "exemplo-local-123456")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "localhost")
    monkeypatch.setenv("FINANCEIRO_DATA_DIR", str(tmp_path))

    async def check():
        async with lifespan(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:10000") as client:
                assert (await client.get("/api/health")).status_code == 200
                assert (await client.get("/")).status_code == 401
                assert (await client.get("/api/backup")).status_code == 401
                assert (await client.get("/api/bootstrap", auth=("demo", "incorreta"))).status_code == 401
                allowed = httpx.BasicAuth("demo", "exemplo-local-123456")
                bootstrap = (await client.get("/api/bootstrap", auth=allowed)).json()
                assert bootstrap["demo_mode"] is True
                assert bootstrap["transaction_count"] == 24
                assert (await client.get("/", auth=allowed)).status_code == 200
                manual = {"date": "2026-09-17", "description": "Exemplo da aula", "amount_cents": -100, "kind": "expense"}
                assert (await client.post("/api/transactions", auth=allowed, json=manual)).status_code == 403
                assert (await client.post("/api/transactions", auth=allowed, json=manual,
                                          headers={"Origin": "https://outro-site.example"})).status_code == 403
                assert (await client.post("/api/transactions", auth=allowed, json=manual,
                                          headers={"Origin": "http://localhost:10000"})).status_code == 201
                assert (await client.get("/api/bootstrap", auth=allowed)).json()["transaction_count"] == 25

    asyncio.run(check())


def test_public_mode_fails_closed_without_password(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCEIRO_DEMO_MODE", "1")
    monkeypatch.delenv("FINANCEIRO_DEMO_PASSWORD", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "localhost")
    monkeypatch.setenv("FINANCEIRO_DATA_DIR", str(tmp_path))

    async def check():
        async with lifespan(app):
            pass

    with pytest.raises(RuntimeError, match="FINANCEIRO_DEMO_PASSWORD"):
        asyncio.run(check())
