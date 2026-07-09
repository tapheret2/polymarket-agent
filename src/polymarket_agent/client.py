from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from polymarket_agent.config import Settings, get_settings
from polymarket_agent.models import Market


class GammaClient:
    """Thin client for Polymarket Gamma (public research API)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = httpx.Client(
            base_url=self.settings.polymarket_gamma_url.rstrip("/"),
            timeout=self.settings.request_timeout,
            headers={
                "User-Agent": self.settings.polymarket_user_agent,
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GammaClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        r = self._client.get(path, params=params or {})
        r.raise_for_status()
        return r.json()

    def list_markets(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        active: bool = True,
        closed: bool = False,
        order: str = "volume24hr",
        ascending: bool = False,
        search: str | None = None,
    ) -> list[Market]:
        params: dict[str, Any] = {
            "limit": limit or self.settings.scan_limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "order": order,
            "ascending": str(ascending).lower(),
        }
        if search:
            # Gamma supports text search via slug/question query on some deployments
            params["tag_slug"] = search if " " not in search else None
        data = self._get("/markets", params={k: v for k, v in params.items() if v is not None})
        if not isinstance(data, list):
            data = data.get("data") or data.get("markets") or []
        markets = [Market.from_gamma(item) for item in data]
        if search:
            q = search.lower()
            markets = [
                m
                for m in markets
                if q in (m.question or "").lower() or q in (m.slug or "").lower()
            ]
        return markets

    def get_market(self, market_id: str) -> Market | None:
        # Try by id path; fall back to list filter
        try:
            data = self._get(f"/markets/{market_id}")
            if isinstance(data, dict) and data.get("question"):
                return Market.from_gamma(data)
        except httpx.HTTPError:
            pass
        for m in self.list_markets(limit=100, order="volume"):
            if m.id == market_id or m.slug == market_id or m.condition_id == market_id:
                return m
        return None

    def search_events(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        params = {"limit": limit, "active": "true", "closed": "false"}
        try:
            data = self._get("/public-search", params={"q": query, **params})
            if isinstance(data, dict):
                return data.get("events") or data.get("markets") or []
            if isinstance(data, list):
                return data
        except httpx.HTTPError:
            pass
        # Fallback: filter markets client-side
        return [m.model_dump(by_alias=True) for m in self.list_markets(limit=limit, search=query)]
