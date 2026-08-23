"""
build_readme.py
Orchestrator: runs ASCII generator and GitHub metrics fetcher,
then populates the README template with live data.
"""

import os
import sys
import re

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.dirname(__file__))

import ascii_generator
import github_metrics

# ── Paths ──────────────────────────────────────────────────────
ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
TEMPLATE_PATH = os.path.join(ROOT_DIR, "templates", "README.template.md")
OUTPUT_PATH = os.path.join(ROOT_DIR, "README.md")


def load_template() -> str:
    """Load the README template file."""
    if not os.path.isfile(TEMPLATE_PATH):
        print(f"ERROR: Template not found at {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def populate_template(template: str, metrics: dict) -> str:
    """
    Replace all {{PLACEHOLDER}} tokens in the template with metric values.
    Unknown placeholders are left intact with a warning.
    """
    replacements = {
        "USERNAME": metrics.get("username", "developer"),
        "TOTAL_CONTRIBUTIONS": f"{metrics.get('total_contributions', 0):,}",
        "CURRENT_STREAK": str(metrics.get("current_streak", 0)),
        "LONGEST_STREAK": str(metrics.get("longest_streak", 0)),
        "ACTIVE_DAYS": str(metrics.get("active_days", 0)),
        "BEST_WEEK": str(metrics.get("best_week", 0)),
        "TOP_LANGUAGE": metrics.get("top_language", "N/A"),
        "YEAR": str(__import__("datetime").datetime.utcnow().year),
        "LAST_UPDATED": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    result = template
    for key, value in replacements.items():
        result = result.replace(f"{{{{{key}}}}}", value)

    # Warn about unresolved placeholders
    unresolved = re.findall(r"\{\{(\w+)\}\}", result)
    if unresolved:
        print(f"WARNING: Unresolved placeholders: {unresolved}", file=sys.stderr)

    return result


def build() -> None:
    """Main pipeline: generate assets → populate template → write README."""
    print("=" * 60)
    print("  GitHub Profile README Builder")
    print("=" * 60)

    # Step 1: Generate ASCII portrait
    print("\n[1/3] Generating ASCII portrait...")
    ascii_generator.generate_portrait()

    # Step 2: Fetch metrics and generate stats SVGs
    print("\n[2/3] Fetching GitHub metrics & generating SVGs...")
    try:
        metrics = github_metrics.fetch_and_generate()
    except Exception as exc:
        print(f"WARNING: Metrics fetch failed: {exc}", file=sys.stderr)
        print("Continuing with placeholder values...", file=sys.stderr)
        metrics = {
            "username": os.environ.get("GITHUB_USERNAME", "Muhammad-Sohair"),
            "total_contributions": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "active_days": 0,
            "best_week": 0,
            "top_language": "N/A",
            "languages": [],
        }
        # Generate placeholder SVGs so the README doesn't reference missing files
        assets_dir = os.path.join(ROOT_DIR, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        github_metrics.generate_sparkline([], os.path.join(assets_dir, "sparkline.svg"))
        github_metrics.generate_streaks_svg({"current": 0, "longest": 0}, os.path.join(assets_dir, "streaks.svg"))
        github_metrics.generate_languages_svg([], os.path.join(assets_dir, "languages.svg"))
        github_metrics.generate_calendar_svg([], os.path.join(assets_dir, "calendar.svg"))

    # Step 3: Populate template and write README
    print("\n[3/3] Building README.md...")
    template = load_template()
    readme_content = populate_template(template, metrics)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\n[OK] README.md written to {OUTPUT_PATH}")
    print("=" * 60)


# ── CLI ────────────────────────────────────────────────────────
if __name__ == "__main__":
    build()
