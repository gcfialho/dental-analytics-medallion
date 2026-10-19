"""Command line entry point: `uv run dental <command>`."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

from dental_analytics.config import Settings


def _pipeline(settings: Settings, args: argparse.Namespace) -> int:
    from dental_analytics.pipeline import run_dbt

    return 0 if run_dbt(settings, "build") else 1


def _brief(settings: Settings, args: argparse.Namespace) -> int:
    from dental_analytics.insights.facts import build_facts
    from dental_analytics.insights.guardrails import verify_brief
    from dental_analytics.insights.offline import build_offline_brief
    from dental_analytics.insights.report import BriefMetadata, save_brief
    from dental_analytics.warehouse import connect

    with connect(settings.duckdb_path) as con:
        facts = build_facts(con)

    use_llm = not args.offline and bool(os.getenv("OPENAI_API_KEY"))
    if use_llm:
        from dental_analytics.insights.llm import generate_brief

        model = args.model or settings.openai_model
        raw = generate_brief(facts, model=model)
        backend = f"openai:{model}"
    else:
        if not args.offline:
            logging.warning("OPENAI_API_KEY is not set; writing the offline brief instead.")
        raw = build_offline_brief(facts)
        backend = "offline"

    verified = verify_brief(raw, facts)
    path = save_brief(settings.reports_dir, raw, verified, BriefMetadata.now(backend))
    print(path.read_text())
    print(
        f"{len(verified.accepted)} findings accepted, {len(verified.rejected)} rejected -> {path}",
        file=sys.stderr,
    )
    failed = bool(verified.rejected or verified.headline_issue)
    return 1 if args.strict and failed else 0


def _dashboard(settings: Settings, args: argparse.Namespace) -> int:
    app = settings.project_root / "src" / "dental_analytics" / "dashboard" / "app.py"
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app), *args.streamlit_args])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dental", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("pipeline", help="Build and test bronze, silver and gold with dbt.")

    brief = sub.add_parser("brief", help="Generate a fact-checked insights brief.")
    brief.add_argument("--offline", action="store_true", help="Skip the LLM and use the deterministic brief.")
    brief.add_argument("--model", help="OpenAI model (default: $OPENAI_MODEL or gpt-5-mini).")
    brief.add_argument("--strict", action="store_true", help="Exit 1 if any finding fails the fact-check.")

    dashboard = sub.add_parser("dashboard", help="Launch the Streamlit dashboard.")
    dashboard.add_argument("streamlit_args", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    handlers = {"pipeline": _pipeline, "brief": _brief, "dashboard": _dashboard}
    return handlers[args.command](Settings.from_env(), args)


if __name__ == "__main__":
    raise SystemExit(main())
