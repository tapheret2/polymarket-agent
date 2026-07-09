from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from polymarket_agent import __version__
from polymarket_agent.agent import PolymarketAgent
from polymarket_agent.config import get_settings

app = typer.Typer(
    name="pm-agent",
    help="Polymarket research agent — scan, rank, paper-trade (no private keys).",
    add_completion=False,
)
console = Console()


def _print_signals(signals, title: str = "Signals") -> None:
    table = Table(title=title, show_lines=False)
    table.add_column("#", style="dim")
    table.add_column("Side")
    table.add_column("Mkt p")
    table.add_column("Edge")
    table.add_column("Score")
    table.add_column("Liq")
    table.add_column("Question")
    for i, s in enumerate(signals, 1):
        side_style = {"YES": "green", "NO": "red", "HOLD": "dim"}.get(s.side, "white")
        table.add_row(
            str(i),
            f"[{side_style}]{s.side}[/{side_style}]",
            f"{s.market_prob:.3f}",
            f"{s.edge:+.3f}",
            f"{s.score:.3f}",
            f"{(s.market.liquidity or 0):,.0f}",
            (s.market.question or "")[:70],
        )
    console.print(table)


@app.command()
def version() -> None:
    """Show package version."""
    console.print(f"polymarket-agent {__version__}")


@app.command()
def scan(
    limit: int = typer.Option(40, help="Max markets to pull"),
    top: int = typer.Option(15, help="Top signals to show"),
    min_liquidity: float = typer.Option(None, help="Override min liquidity"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Filter question text"),
    save: bool = typer.Option(True, help="Write JSON snapshot under data/raw"),
) -> None:
    """Scan active markets and rank research signals."""
    settings = get_settings()
    if min_liquidity is not None:
        settings.min_liquidity = min_liquidity
    agent = PolymarketAgent(settings)
    try:
        markets = agent.scan(limit=limit, query=query)
        signals = agent.analyze(markets)[:top]
        _print_signals(signals, title=f"Top {len(signals)} / {len(markets)} markets")
        if save and signals:
            path = agent.snapshot(signals)
            console.print(f"[dim]snapshot → {path}[/dim]")
    finally:
        agent.close()


@app.command("paper-run")
def paper_run(
    limit: int = typer.Option(40),
    top: int = typer.Option(10),
    max_trades: int = typer.Option(3, help="Max paper fills this run"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),
) -> None:
    """Scan and paper-trade top positive-edge signals (local JSON only)."""
    agent = PolymarketAgent()
    try:
        signals = agent.run_once(
            limit=limit, top_k=top, query=query, paper_trade=True, max_paper=max_trades
        )
        _print_signals(signals)
        console.print(agent.paper.summary())
    finally:
        agent.close()


@app.command("paper-status")
def paper_status() -> None:
    """Show paper book summary."""
    agent = PolymarketAgent()
    try:
        console.print(agent.paper.summary())
        fills = agent.paper.book.fills[-5:]
        if fills:
            table = Table(title="Last fills")
            table.add_column("Side")
            table.add_column("Price")
            table.add_column("Notional")
            table.add_column("Question")
            for f in fills:
                table.add_row(f.side, f"{f.price:.3f}", f"{f.notional:.2f}", f.question[:60])
            console.print(table)
    finally:
        agent.close()


@app.command()
def search(q: str = typer.Argument(..., help="Search text")) -> None:
    """Search markets by keyword (client-side filter on Gamma list)."""
    agent = PolymarketAgent()
    try:
        markets = agent.scan(limit=100, min_liquidity=0, query=q)
        signals = agent.analyze(markets)[:20]
        _print_signals(signals, title=f"Search: {q}")
    finally:
        agent.close()


if __name__ == "__main__":
    app()
