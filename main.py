#!/usr/bin/env python3
"""Talaash CLI — conversational local AI file search."""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text

console = Console()
logging.getLogger("talaash").setLevel(logging.WARNING)

# ── Response copy ─────────────────────────────────────────────────────────────

_FOUND_OPENERS = [
    "I went through your files and here's what I found:",
    "Sure! I scanned your documents. These look most relevant:",
    "Found it! Here's what matched:",
    "I searched your files. These are the closest matches:",
    "Here's what I found in your documents:",
]
_NOT_FOUND = [
    "I couldn't find any files matching that. Try different keywords, or make sure the folder is indexed.",
    "Nothing came up. The file might not be indexed yet — run:\n`python main.py index --folder <path>`",
    "No matches found. Try describing it differently, or check that the right folder is indexed.",
]
_GREETINGS = {"hi", "hello", "hey", "hlo", "hii", "namaste", "नमस्ते"}
_THANKS = {"thanks", "thank you", "thx", "ty", "great", "perfect", "nice", "good"}
_HELP_WORDS = {"help", "what can you do", "how does this work"}


# ── Presentation helpers ──────────────────────────────────────────────────────

def _ai(text: str) -> None:
    """Print a panel styled as the AI's response."""
    console.print()
    console.print(
        Panel(
            Markdown(text),
            border_style="cyan",
            title="[bold cyan]Talaash[/bold cyan]",
            title_align="left",
            padding=(0, 1),
        )
    )
    console.print()


def _describe_results(results: list[dict], total_indexed: int) -> str:
    """Build a natural-language response from search results."""
    lines = [random.choice(_FOUND_OPENERS), ""]
    for i, r in enumerate(results, 1):
        score = r["relevance_score"]
        confidence = (
            "Strong match" if score >= 85
            else "Possible match" if score >= 65
            else "Weak match"
        )
        doc_type = r["file_type"].replace("_", " ").title()
        lines += [
            f"**{i}. {r['file_name']}** — {doc_type} · {score}% · *{confidence}*",
            f"   📁 `{r['file_path']}`",
            f"   > {r['preview_text']}" if r["preview_text"] else "",
            "",
        ]
    top = results[0]
    if top["relevance_score"] >= 85:
        lines.append(f"**{top['file_name']}** looks like the best match. Open it to confirm.")
    elif top["relevance_score"] >= 65:
        lines.append(f"Check **{top['file_name']}** first — it's the closest match.")
    else:
        lines.append(
            "These are the closest matches I found, but confidence is low. "
            "Try rephrasing or make sure the right folder is indexed."
        )
    return "\n".join(lines)


# ── Small-talk / command handling ─────────────────────────────────────────────

def _handle_special(query: str, index_svc, search_svc) -> bool:
    q = query.lower().strip()

    if q in ("quit", "exit", "q", "bye"):
        _ai("Goodbye! Come back whenever you need to find something.")
        sys.exit(0)

    if q in _GREETINGS or any(q.startswith(g) for g in _GREETINGS):
        _ai(
            "Hey! I'm Talaash — your local AI file assistant.\n\n"
            "Just tell me what you're looking for. Examples:\n"
            "  • *find files with ramesh kumar*\n"
            "  • *my aadhaar card*\n"
            "  • *salary slip june 2024*\n"
            "  • *income tax return last year*"
        )
        return True

    if q in _THANKS:
        _ai("Glad I could help! What else are you looking for?")
        return True

    if q in _HELP_WORDS:
        _ai(
            "I search through the **content** of your files — not just filenames.\n\n"
            "Try:\n"
            "  • *bank statement with account number*\n"
            "  • *aadhaar card for ankit verma*\n"
            "  • *ITR form 2023*\n"
            "  • *please find files containing phone number 9876543210*\n\n"
            "Type **stats** to see what's indexed, **quit** to exit."
        )
        return True

    if q == "stats":
        _show_stats(index_svc)
        return True

    if q == "clear":
        _do_clear(index_svc)
        return True

    return False


def _show_stats(index_svc) -> None:
    stats = index_svc.get_stats()
    total = index_svc.get_count()
    if total == 0:
        _ai("Index is empty. Use `python main.py index --folder <path>` to add documents.")
        return
    lines = [f"I have **{total} files** indexed:\n"]
    for dtype, count in sorted(stats.items(), key=lambda x: -x[1]):
        lines.append(f"  • {dtype.replace('_', ' ').title()}: **{count}**")
    _ai("\n".join(lines))


def _do_clear(index_svc) -> None:
    confirm = Prompt.ask(
        "  [yellow]Clear the entire index?[/yellow] [dim](yes / no)[/dim]"
    ).strip().lower()
    if confirm in ("yes", "y"):
        index_svc.clear()
        _ai("Done. Index has been cleared.")
    else:
        _ai("Alright, index left untouched.")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_interactive(_args: argparse.Namespace, index_svc, search_svc) -> None:
    """Conversational search REPL."""
    console.print()
    console.print(Rule("[bold cyan]Talaash[/bold cyan]  [dim]AI File Assistant[/dim]"))
    console.print()

    if index_svc.get_count() == 0:
        _ai(
            "Your index is empty — I have no files to search yet.\n\n"
            "Add a folder first:\n"
            "```\npython main.py index --folder /path/to/your/documents\n```"
        )
        sys.exit(0)

    console.print("  [dim]Loading AI model...[/dim]", end="")
    index_svc.embedder.load()
    total = index_svc.get_count()
    console.print(f" [green]ready.[/green]  [dim]{total} files indexed.[/dim]\n")

    _ai(
        f"Hi! I've got **{total} files** indexed and ready to search.\n\n"
        "Just tell me what you're looking for — English, Hindi, or Marathi.\n"
        "Example: *please find files with ramesh kumar* or *my salary slip from june*"
    )

    while True:
        try:
            user_label = Text()
            user_label.append("  You  ", style="bold white on blue")
            console.print(user_label, end=" ")
            query = console.input("").strip()
        except (KeyboardInterrupt, EOFError):
            _ai("Goodbye!")
            break

        if not query:
            continue

        if _handle_special(query, index_svc, search_svc):
            continue

        with console.status("  [dim]Searching through your files...[/dim]", spinner="dots"):
            results = search_svc.search(query, n_results=3)

        if not results:
            _ai(random.choice(_NOT_FOUND))
        else:
            _ai(_describe_results(results, total))


def cmd_index(args: argparse.Namespace, index_svc) -> None:
    """Index a folder and optionally watch it for changes."""
    logging.getLogger("talaash").setLevel(logging.INFO)

    folder = args.folder
    if not Path(folder).is_dir():
        console.print(f"[red]Error:[/red] '{folder}' is not a valid directory.")
        sys.exit(1)

    console.print(f"\n[bold cyan]Talaash[/bold cyan] — Indexing [bold]{folder}[/bold]\n")
    summary = index_svc.index_folder(folder, recursive=True)

    console.print(
        f"\n[green]Done.[/green] Indexed [bold]{summary['indexed']}[/bold] files.",
        end="",
    )
    if summary.get("errors", 0):
        console.print(f"  [yellow]{summary['errors']} could not be read.[/yellow]")
    else:
        console.print()

    if args.watch:
        from src.indexer.watcher import FileWatcher
        watcher = FileWatcher(index_svc)
        watcher.start(folder)
        console.print("\n[dim]Watching for new files. Press Ctrl+C to stop.[/dim]")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()


def cmd_server(_args: argparse.Namespace) -> None:
    """Start the FastAPI server."""
    from src.api.server import start_server
    start_server()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(prog="talaash")
    sub = parser.add_subparsers(dest="command")

    p_index = sub.add_parser("index", help="Index a folder")
    p_index.add_argument("--folder", required=True)
    p_index.add_argument("--watch", action="store_true")

    sub.add_parser("server", help="Start the REST API server")

    args = parser.parse_args()

    # server doesn't need services (uvicorn wires its own via FastAPI DI)
    if args.command == "server":
        cmd_server(args)
        return

    # All other commands: create services once here, pass down
    from src.services import create_services
    from src.utils.config import settings
    index_svc, search_svc = create_services(settings)

    if args.command == "index":
        cmd_index(args, index_svc)
    else:
        cmd_interactive(args, index_svc, search_svc)


if __name__ == "__main__":
    main()
