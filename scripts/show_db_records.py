"""
Display PostgreSQL Records for Screenshots & Audit
Translation Quality Analytics & Continuous Improvement Platform

Fetches and displays live translations, options, and human feedback from PostgreSQL
in a clean, formatted terminal table for report screenshots.
"""

import sys
from pathlib import Path

# Ensure project root in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configure UTF-8 stdout encoding for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.table import Table
from sqlalchemy import desc, select

from src.database.connection import check_db_health, get_db_session
from src.database.models import Feedback, Translation, TranslationOption

console = Console()


def display_database_records():
    health = check_db_health()
    if health.get("status") != "healthy":
        console.print(f"[bold red]Database connection failed:[/bold red] {health.get('error')}")
        console.print("[yellow]Please start Docker Desktop and run: [bold]docker compose up -d[/bold][/yellow]")
        return

    console.print("\n[bold cyan]========================================================================[/bold cyan]")
    console.print("[bold green]  POSTGRESQL LIVE DATABASE AUDIT - TRANSLATIONS & FEEDBACK RECORDS[/bold green]")
    console.print("[bold cyan]========================================================================[/bold cyan]\n")

    with get_db_session() as sess:
        translations = sess.execute(
            select(Translation).order_by(desc(Translation.created_at)).limit(10)
        ).scalars().all()

        if not translations:
            console.print("[yellow]No translations logged in database yet.[/yellow]")
            return

        table = Table(
            title="Recent Translation Requests (Live PostgreSQL Table: 'translations')",
            header_style="bold magenta",
            border_style="cyan"
        )
        table.add_column("Request ID", style="bold green", width=22)
        table.add_column("Timestamp (UTC)", width=17)
        table.add_column("Pair", style="bold yellow", width=10)
        table.add_column("Latency", justify="right", width=9)
        table.add_column("Quality", justify="center", width=10)
        table.add_column("Anomaly", width=12)
        table.add_column("Preferred", width=10)
        table.add_column("Feedback", width=10)
        table.add_column("Defect Reason", style="red", width=18)

        for t in translations:
            req_id = t.request_id or str(t.id)[:8]
            t_stamp = t.created_at.strftime("%Y-%m-%d %H:%M")
            pair = f"{t.source_language.upper()} -> {t.target_language.upper()}"
            lat = f"{t.translation_time_ms / 1000.0:.2f}s"
            score = f"{t.quality_score:.1f}" if t.quality_score is not None else "N/A"
            anom = "[bold red]YES[/bold red]" if t.anomaly_flag else "[green]NO[/green]"

            # Check preferred style
            pref_style = "—"
            rating = "Pending"
            defect = "—"

            for opt in t.options:
                if opt.user_selected:
                    pref_style = opt.style_option.capitalize()
                if opt.feedback:
                    rating = opt.feedback.rating
                    defect = opt.feedback.reason or "None"

            rating_display = f"[bold green]{rating}[/bold green]" if rating == "GOOD" else (f"[bold red]{rating}[/bold red]" if rating == "POOR" else rating)
            defect_display = f"[bold red]{defect}[/bold red]" if defect not in ("—", "None") else defect

            table.add_row(
                req_id,
                t_stamp,
                pair,
                lat,
                score,
                anom,
                pref_style,
                rating_display,
                defect_display
            )

        console.print(table)
        console.print("\n[bold green]✓ Live database query executed successfully.[/bold green]\n")


if __name__ == "__main__":
    display_database_records()
