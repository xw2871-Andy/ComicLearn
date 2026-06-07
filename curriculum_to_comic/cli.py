"""Command-line entry point.

Examples
--------

# Pure-topic mode (no source file)::

    c2c topic "Riemann Sums" --grade "AP Calculus AB"

# From a markdown lesson outline::

    c2c markdown ./lesson_outline.md --grade "AP Calculus AB" --topic "L'Hopital"

# From a textbook PDF::

    c2c pdf ./thomas_calculus.pdf --topic "Riemann Sums" \\
            --grade "AP Calculus AB" --pages 380-400
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .agent import ComicAgent
from .claude_client import ClaudeClient
from .extractors import from_markdown, from_pdf, from_topic

console = Console()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="curriculum-to-comic")
def main() -> None:
    """Turn an educational curriculum into a comic book lesson with Claude."""


# ----- Shared options ------------------------------------------------------ #


def _shared(f):
    f = click.option(
        "--grade",
        required=True,
        help="Grade level / course, e.g. 'AP Calculus AB', '7th-grade Math'.",
    )(f)
    f = click.option(
        "--cast",
        multiple=True,
        help="Recurring characters (repeat for multiple, default Doraemon/Nobita).",
    )(f)
    f = click.option(
        "--setting",
        default=None,
        help="Optional setting hint, e.g. 'Tokyo middle school', 'space station'.",
    )(f)
    f = click.option(
        "--reference",
        "references",
        multiple=True,
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        help=(
            "Reference comic page / character sheet to anchor visual style. "
            "Repeat the flag for multiple. Sent to Nano Banana 2 with every "
            "panel request. Ignored by the 'svg' backend."
        ),
    )(f)
    f = click.option(
        "--no-chain",
        "no_chain",
        is_flag=True,
        default=False,
        help=(
            "Disable the rolling self-reference (each new panel is normally "
            "conditioned on the previous panel for visual consistency)."
        ),
    )(f)
    f = click.option(
        "--no-qa",
        "no_qa",
        is_flag=True,
        default=False,
        help=(
            "Skip the visual-consistency QA subagent. By default each panel "
            "is reviewed by Claude vision and failing panels are re-rendered."
        ),
    )(f)
    f = click.option(
        "--qa-retries",
        "qa_retries",
        type=int,
        default=1,
        show_default=True,
        help=(
            "How many times to re-render a panel whose QA verdict is 'fail' "
            "before giving up and shipping it anyway."
        ),
    )(f)
    f = click.option(
        "--out",
        "out_dir",
        type=click.Path(file_okay=False, path_type=Path),
        default=None,
        help="Output directory (defaults to ./outputs).",
    )(f)
    return f


# ----- Sub-commands -------------------------------------------------------- #


@main.command("topic")
@click.argument("topic")
@_shared
def topic_cmd(
    topic: str,
    grade: str,
    cast: tuple[str, ...],
    setting: str | None,
    references: tuple[Path, ...],
    no_chain: bool,
    no_qa: bool,
    qa_retries: int,
    out_dir: Path | None,
) -> None:
    """Generate a comic from just a topic + grade level."""

    agent = _agent(out_dir, cast, setting, references, no_chain, no_qa, qa_retries)
    inp = from_topic(topic, grade)
    result = agent.run(inp)
    _success(result.book.pdf_path)


@main.command("markdown")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--topic", default=None, help="Override the title (else inferred).")
@_shared
def markdown_cmd(
    path: Path,
    topic: str | None,
    grade: str,
    cast: tuple[str, ...],
    setting: str | None,
    references: tuple[Path, ...],
    no_chain: bool,
    no_qa: bool,
    qa_retries: int,
    out_dir: Path | None,
) -> None:
    """Generate a comic from a markdown / text lesson outline."""

    agent = _agent(out_dir, cast, setting, references, no_chain, no_qa, qa_retries)
    inp = from_markdown(path, topic, grade)
    result = agent.run(inp)
    _success(result.book.pdf_path)


@main.command("pdf")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--topic", required=True, help="Specific topic to focus on within the PDF.")
@click.option(
    "--pages",
    default=None,
    help="Page range to read, e.g. '380-400'. Whole PDF if omitted.",
)
@_shared
def pdf_cmd(
    path: Path,
    topic: str,
    pages: str | None,
    grade: str,
    cast: tuple[str, ...],
    setting: str | None,
    references: tuple[Path, ...],
    no_chain: bool,
    no_qa: bool,
    qa_retries: int,
    out_dir: Path | None,
) -> None:
    """Generate a comic from a textbook PDF page range."""

    agent = _agent(out_dir, cast, setting, references, no_chain, no_qa, qa_retries)
    page_range = _parse_pages(pages) if pages else None
    inp = from_pdf(
        path,
        topic=topic,
        grade_level=grade,
        page_range=page_range,
        claude=ClaudeClient(),
    )
    result = agent.run(inp)
    _success(result.book.pdf_path)


# ----- Helpers ------------------------------------------------------------- #


def _agent(
    out_dir: Path | None,
    cast: tuple[str, ...],
    setting: str | None,
    references: tuple[Path, ...],
    no_chain: bool,
    no_qa: bool,
    qa_retries: int,
) -> ComicAgent:
    return ComicAgent(
        output_dir=out_dir,
        cast=list(cast) if cast else None,
        setting_hint=setting,
        reference_paths=list(references) if references else None,
        chain_panels=not no_chain,
        run_qa=not no_qa,
        qa_retries=qa_retries,
    )


def _parse_pages(spec: str) -> tuple[int, int]:
    try:
        lo, hi = spec.split("-", 1)
        return int(lo), int(hi)
    except ValueError as exc:
        raise click.BadParameter(
            "Expected --pages in the form 'lo-hi', e.g. '380-400'."
        ) from exc


def _success(pdf_path: str) -> None:
    console.print(f"\n[bold green]✔ Comic book ready:[/bold green] {pdf_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted.[/red]")
        sys.exit(130)
