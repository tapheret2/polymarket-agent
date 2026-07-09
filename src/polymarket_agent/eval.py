from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from polymarket_agent.client import GammaClient
from polymarket_agent.config import Settings, get_settings
from polymarket_agent.models import Market
from polymarket_agent.resolution import brier_score, infer_binary_outcome, log_loss


@dataclass
class EvalRow:
    snapshot_ts: str
    question: str
    slug: str | None
    forecast_yes: float
    source: str  # market | model
    side: str
    outcome: int | None
    brier: float | None
    logloss: float | None
    resolved: bool


@dataclass
class EvalReport:
    rows: list[EvalRow] = field(default_factory=list)
    report_path: str | None = None

    @property
    def resolved_rows(self) -> list[EvalRow]:
        return [r for r in self.rows if r.resolved and r.brier is not None]

    def mean_brier(self, source: str | None = None) -> float | None:
        rows = self.resolved_rows
        if source:
            rows = [r for r in rows if r.source == source]
        if not rows:
            return None
        return sum(r.brier or 0.0 for r in rows) / len(rows)

    def mean_logloss(self, source: str | None = None) -> float | None:
        rows = self.resolved_rows
        if source:
            rows = [r for r in rows if r.source == source]
        if not rows:
            return None
        return sum(r.logloss or 0.0 for r in rows) / len(rows)

    def summary(self) -> dict[str, Any]:
        return {
            "n_rows": len(self.rows),
            "n_resolved_pairs": len(self.resolved_rows),
            "brier_market": self.mean_brier("market"),
            "brier_model": self.mean_brier("model"),
            "logloss_market": self.mean_logloss("market"),
            "logloss_model": self.mean_logloss("model"),
            "report_path": self.report_path,
        }


def load_snapshots(raw_dir: Path) -> list[dict[str, Any]]:
    files = sorted(raw_dir.glob("scan_*.json"))
    out: list[dict[str, Any]] = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def _match_market(cache: dict[str, Market], slug: str | None, question: str) -> Market | None:
    if slug and slug in cache:
        return cache[slug]
    if question in cache:
        return cache[question]
    return None


def evaluate_snapshots(
    *,
    settings: Settings | None = None,
    client: GammaClient | None = None,
    limit_fetch: int = 200,
) -> EvalReport:
    """Join historical scan forecasts with market resolution when available."""
    settings = settings or get_settings()
    raw_dir = settings.data_dir / "raw"
    snaps = load_snapshots(raw_dir)
    report = EvalReport()
    if not snaps:
        return report

    own_client = client is None
    client = client or GammaClient(settings)
    cache: dict[str, Market] = {}
    try:
        for closed_flag in (False, True):
            batch = client.list_markets(
                limit=limit_fetch,
                active=not closed_flag,
                closed=closed_flag,
                order="volume",
            )
            for m in batch:
                if m.slug:
                    cache[m.slug] = m
                cache[m.question] = m

        for snap in snaps:
            ts = str(snap.get("ts") or "")
            for s in snap.get("signals") or []:
                q = s.get("question") or ""
                slug = s.get("slug")
                m = _match_market(cache, slug, q)
                outcome = infer_binary_outcome(m) if m else None
                resolved = outcome is not None

                market_p = s.get("market_prob")
                model_p = s.get("model_prob")
                # analyzer stores model_prob as P(YES)
                pairs = []
                if market_p is not None:
                    pairs.append(("market", float(market_p)))
                if model_p is not None:
                    pairs.append(("model", float(model_p)))

                for source, f_yes in pairs:
                    b = brier_score(f_yes, outcome) if resolved else None
                    ll = log_loss(f_yes, outcome) if resolved else None
                    report.rows.append(
                        EvalRow(
                            snapshot_ts=ts,
                            question=q,
                            slug=slug,
                            forecast_yes=f_yes,
                            source=source,
                            side=str(s.get("side") or "?"),
                            outcome=outcome,
                            brier=b,
                            logloss=ll,
                            resolved=resolved,
                        )
                    )
    finally:
        if own_client:
            client.close()

    out = (
        settings.data_dir
        / "processed"
        / f"eval_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": report.summary(),
        "rows": [asdict(r) for r in report.rows],
    }
    # fill path after write target known
    payload["summary"]["report_path"] = str(out)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report.report_path = str(out)
    return report


def benchmark_closed_sample(
    *,
    n: int = 50,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Score market mid on closed markets (expect low Brier when prices pin)."""
    settings = settings or get_settings()
    with GammaClient(settings) as client:
        markets = client.list_markets(limit=n, active=False, closed=True, order="volume")
    briers: list[float] = []
    for m in markets:
        o = infer_binary_outcome(m)
        if o is None or m.yes_price is None:
            continue
        briers.append(brier_score(m.yes_price, o))
    return {
        "n_closed_scored": len(briers),
        "mean_brier_at_close": (sum(briers) / len(briers)) if briers else None,
        "note": "Near-zero mean Brier expected when YES/NO prices pin to 0/1",
    }
