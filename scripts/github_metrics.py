"""
github_metrics.py
Fetches GitHub profile metrics via GraphQL API and generates
standalone SVG visualizations: sparkline, streaks, languages, calendar.
"""

import os
import sys
import json
import math
import time
from datetime import datetime, timedelta
from typing import Any

import requests

# ── Configuration ──────────────────────────────────────────────
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
BG_COLOR = "#0d1117"
FG_COLOR = "#c9d1d9"
ACCENT = "#58a6ff"
MUTED = "#484f58"
GREEN_SHADES = ["#0d1117", "#0e4429", "#006d32", "#26a641", "#39d353"]
FONT_FAMILY = "'JetBrains Mono', monospace"
FONT_IMPORT = "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&amp;display=swap"

GRAPHQL_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def _get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required.")
    return token


def _get_username() -> str:
    """Return username from env or query the authenticated user."""
    username = os.environ.get("GITHUB_USERNAME", "Muhammad-Sohair")
    if username:
        return username
    token = _get_token()
    resp = requests.get(
        f"{REST_URL}/user",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["login"]


def _graphql(query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query with retry/backoff for rate limits."""
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(GRAPHQL_URL, json=payload, headers=headers, timeout=30)

            # Rate-limit handling
            if resp.status_code == 403 or resp.status_code == 429:
                reset = resp.headers.get("X-RateLimit-Reset")
                wait = RETRY_DELAY * attempt
                if reset:
                    wait = max(int(reset) - int(time.time()) + 1, wait)
                print(f"Rate limited. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})...", file=sys.stderr)
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                print(f"GraphQL errors: {json.dumps(data['errors'], indent=2)}", file=sys.stderr)
            return data.get("data", {})

        except requests.exceptions.RequestException as exc:
            print(f"Request failed (attempt {attempt}/{MAX_RETRIES}): {exc}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    print("ERROR: All GraphQL retries exhausted.", file=sys.stderr)
    return {}


# ── Data Fetching ──────────────────────────────────────────────

def fetch_contribution_data(username: str) -> dict[str, Any]:
    """Fetch contribution calendar for the last year."""
    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    data = _graphql(query, {"username": username})
    if not data:
        return {"total": 0, "weeks": [], "days": []}

    calendar = data.get("user", {}).get("contributionsCollection", {}).get("contributionCalendar", {})
    total = calendar.get("totalContributions", 0)
    weeks = calendar.get("weeks", [])

    # Flatten daily counts
    days: list[dict] = []
    for week in weeks:
        for day in week.get("contributionDays", []):
            days.append({
                "date": day["date"],
                "count": day["contributionCount"],
                "weekday": day["weekday"],
            })

    return {"total": total, "weeks": weeks, "days": days}


def fetch_languages(username: str) -> list[dict]:
    """Fetch language breakdown by bytes across all public repos (paginated)."""
    languages: dict[str, int] = {}
    cursor = None

    for _ in range(10):  # max 10 pages × 50 repos = 500 repos
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        query($username: String!) {{
          user(login: $username) {{
            repositories(first: 50, ownerAffiliations: OWNER, privacy: PUBLIC{after}) {{
              pageInfo {{ hasNextPage endCursor }}
              nodes {{
                languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
                  edges {{
                    size
                    node {{ name color }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """
        data = _graphql(query, {"username": username})
        repos = data.get("user", {}).get("repositories", {})
        nodes = repos.get("nodes", [])

        for repo in nodes:
            for edge in repo.get("languages", {}).get("edges", []):
                name = edge["node"]["name"]
                color = edge["node"].get("color", MUTED)
                size = edge["size"]
                if name not in languages:
                    languages[name] = 0
                languages[name] += size

        page_info = repos.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    # Sort by bytes descending
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    total_bytes = sum(b for _, b in sorted_langs) or 1

    # Re-fetch colors
    color_map = _fetch_language_colors(username)

    result = []
    for name, byte_count in sorted_langs[:10]:  # top 10
        result.append({
            "name": name,
            "bytes": byte_count,
            "percent": round(byte_count / total_bytes * 100, 1),
            "color": color_map.get(name, MUTED),
        })
    return result


def _fetch_language_colors(username: str) -> dict[str, str]:
    """Quick pass to collect language colors."""
    query = """
    query($username: String!) {
      user(login: $username) {
        repositories(first: 20, ownerAffiliations: OWNER, privacy: PUBLIC, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            languages(first: 10) {
              edges {
                node { name color }
              }
            }
          }
        }
      }
    }
    """
    data = _graphql(query, {"username": username})
    colors: dict[str, str] = {}
    for repo in data.get("user", {}).get("repositories", {}).get("nodes", []):
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            color = edge["node"].get("color")
            if color and name not in colors:
                colors[name] = color
    return colors


# ── Metric Calculations ───────────────────────────────────────

def compute_streaks(days: list[dict]) -> dict:
    """Compute current streak and longest streak from daily contribution data."""
    if not days:
        return {"current": 0, "longest": 0}

    # Sort by date
    sorted_days = sorted(days, key=lambda d: d["date"])
    today = datetime.utcnow().strftime("%Y-%m-%d")

    current = 0
    longest = 0
    streak = 0

    for day in sorted_days:
        if day["count"] > 0:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 0

    # Current streak: count backwards from today
    current = 0
    for day in reversed(sorted_days):
        if day["date"] > today:
            continue
        if day["count"] > 0:
            current += 1
        else:
            break

    return {"current": current, "longest": longest}


def compute_activity_stats(days: list[dict]) -> dict:
    """Compute active days and best week."""
    active_days = sum(1 for d in days if d["count"] > 0)
    best_week = 0
    for i in range(len(days) - 6):
        week_total = sum(days[j]["count"] for j in range(i, i + 7))
        best_week = max(best_week, week_total)
    return {"active_days": active_days, "best_week": best_week}


# ── SVG Generators ─────────────────────────────────────────────

def _svg_header(width: float, height: float) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">\n'
        f'  <style>\n'
        f"    @import url('{FONT_IMPORT}');\n"
        f"    text {{ font-family: {FONT_FAMILY}; fill: {FG_COLOR}; }}\n"
        f'  </style>\n'
        f'  <rect width="100%" height="100%" fill="{BG_COLOR}" rx="6" />\n'
    )


def generate_sparkline(days: list[dict], output_path: str) -> None:
    """Generate a 52-week contribution sparkline SVG."""
    if not days:
        _write_placeholder(output_path, "No contribution data", 500, 100)
        return

    # Aggregate by week
    week_totals: list[int] = []
    chunk_size = 7
    for i in range(0, len(days), chunk_size):
        week = days[i:i + chunk_size]
        week_totals.append(sum(d["count"] for d in week))

    width, height = 500, 100
    pad_x, pad_y = 15, 20
    chart_w = width - 2 * pad_x
    chart_h = height - 2 * pad_y
    max_val = max(week_totals) if week_totals else 1

    points = []
    n = len(week_totals)
    for i, val in enumerate(week_totals):
        x = pad_x + (i / max(n - 1, 1)) * chart_w
        y = pad_y + chart_h - (val / max_val) * chart_h
        points.append(f"{x:.1f},{y:.1f}")

    # Build filled area
    area_points = points.copy()
    area_points.append(f"{pad_x + chart_w:.1f},{pad_y + chart_h:.1f}")
    area_points.append(f"{pad_x:.1f},{pad_y + chart_h:.1f}")

    svg = _svg_header(width, height)
    # Gradient fill under the line
    svg += '  <defs>\n'
    svg += f'    <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">\n'
    svg += f'      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.3" />\n'
    svg += f'      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0.02" />\n'
    svg += '    </linearGradient>\n'
    svg += '  </defs>\n'
    svg += f'  <polyline points="{" ".join(area_points)}" fill="url(#sparkGrad)" stroke="none" />\n'
    svg += f'  <polyline points="{" ".join(points)}" fill="none" stroke="{ACCENT}" stroke-width="1.5" stroke-linejoin="round" />\n'
    # End dot
    if points:
        last = points[-1]
        lx, ly = last.split(",")
        svg += f'  <circle cx="{lx}" cy="{ly}" r="3" fill="{ACCENT}" />\n'
    svg += '</svg>'

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Sparkline SVG -> {output_path}")


def generate_streaks_svg(streaks: dict, output_path: str) -> None:
    """Generate a two-stat streak card SVG."""
    width, height = 340, 120
    svg = _svg_header(width, height)

    # Current streak
    svg += f'  <text x="85" y="40" text-anchor="middle" font-size="11" fill="{MUTED}">Current Streak</text>\n'
    svg += f'  <text x="85" y="78" text-anchor="middle" font-size="32" font-weight="bold" fill="{ACCENT}">{streaks["current"]}</text>\n'
    svg += f'  <text x="85" y="98" text-anchor="middle" font-size="11" fill="{MUTED}">days</text>\n'

    # Divider
    svg += f'  <line x1="170" y1="20" x2="170" y2="100" stroke="{MUTED}" stroke-width="0.5" />\n'

    # Longest streak
    svg += f'  <text x="255" y="40" text-anchor="middle" font-size="11" fill="{MUTED}">Longest Streak</text>\n'
    svg += f'  <text x="255" y="78" text-anchor="middle" font-size="32" font-weight="bold" fill="{FG_COLOR}">{streaks["longest"]}</text>\n'
    svg += f'  <text x="255" y="98" text-anchor="middle" font-size="11" fill="{MUTED}">days</text>\n'

    svg += '</svg>'
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Streaks SVG -> {output_path}")


def generate_languages_svg(languages: list[dict], output_path: str) -> None:
    """Generate a horizontal stacked bar + legend SVG for language breakdown."""
    if not languages:
        _write_placeholder(output_path, "No language data", 500, 200)
        return

    width = 500
    bar_y = 35
    bar_h = 14
    pad_x = 20
    bar_w = width - 2 * pad_x
    legend_start_y = bar_y + bar_h + 25
    legend_row_h = 22
    num_langs = len(languages)
    height = legend_start_y + math.ceil(num_langs / 2) * legend_row_h + 20

    svg = _svg_header(width, height)
    svg += f'  <text x="{pad_x}" y="22" font-size="12" font-weight="bold">Languages</text>\n'

    # Stacked bar with rounded clip
    svg += f'  <clipPath id="barClip"><rect x="{pad_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="4" /></clipPath>\n'
    svg += f'  <g clip-path="url(#barClip)">\n'
    x_offset = pad_x
    for lang in languages:
        seg_w = max(lang["percent"] / 100 * bar_w, 1)
        svg += f'    <rect x="{x_offset:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" fill="{lang["color"]}" />\n'
        x_offset += seg_w
    svg += '  </g>\n'

    # Legend – 2 columns
    col_w = (width - 2 * pad_x) / 2
    for i, lang in enumerate(languages):
        col = i % 2
        row = i // 2
        lx = pad_x + col * col_w
        ly = legend_start_y + row * legend_row_h

        svg += f'  <circle cx="{lx + 5}" cy="{ly}" r="4" fill="{lang["color"]}" />\n'
        svg += f'  <text x="{lx + 14}" y="{ly + 4}" font-size="11">{lang["name"]}</text>\n'
        svg += f'  <text x="{lx + 14 + len(lang["name"]) * 7}" y="{ly + 4}" font-size="11" fill="{MUTED}"> {lang["percent"]}%</text>\n'

    svg += '</svg>'
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Languages SVG -> {output_path}")


def generate_calendar_svg(weeks: list[dict], output_path: str) -> None:
    """Generate a minimalist yearly contribution calendar (52×7 grid)."""
    if not weeks:
        _write_placeholder(output_path, "No calendar data", 720, 130)
        return

    cell = 11
    gap = 3
    pad_x, pad_y = 30, 25
    num_weeks = len(weeks)
    width = pad_x + num_weeks * (cell + gap) + 10
    height = pad_y + 7 * (cell + gap) + 25

    # Find max for color mapping
    all_counts = []
    for w in weeks:
        for d in w.get("contributionDays", []):
            all_counts.append(d["contributionCount"])
    max_count = max(all_counts) if all_counts else 1

    svg = _svg_header(width, height)
    svg += f'  <text x="{pad_x}" y="16" font-size="12" font-weight="bold">Contributions</text>\n'

    # Day labels
    day_labels = ["", "Mon", "", "Wed", "", "Fri", ""]
    for i, label in enumerate(day_labels):
        if label:
            y = pad_y + i * (cell + gap) + cell - 1
            svg += f'  <text x="2" y="{y}" font-size="9" fill="{MUTED}">{label}</text>\n'

    # Cells
    for wi, week in enumerate(weeks):
        for day in week.get("contributionDays", []):
            wd = day["weekday"]
            count = day["contributionCount"]
            # Map count to color shade
            if count == 0:
                color = GREEN_SHADES[0]
            else:
                level = min(int(count / max_count * 4) + 1, 4)
                color = GREEN_SHADES[level]

            x = pad_x + wi * (cell + gap)
            y = pad_y + wd * (cell + gap)
            svg += f'  <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{color}" />\n'

    svg += '</svg>'
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Calendar SVG -> {output_path}")


def _write_placeholder(path: str, message: str, w: int, h: int) -> None:
    """Write a placeholder SVG with a centered message."""
    svg = _svg_header(w, h)
    svg += f'  <text x="{w / 2}" y="{h / 2}" text-anchor="middle" font-size="13" fill="{MUTED}">{message}</text>\n'
    svg += '</svg>'
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


# ── Public API ─────────────────────────────────────────────────

def fetch_and_generate() -> dict[str, Any]:
    """
    Main entry point: fetch all metrics, generate SVGs, return metrics dict.
    """
    os.makedirs(ASSETS_DIR, exist_ok=True)

    username = _get_username()
    print(f"Fetching metrics for @{username}...")

    # 1. Contributions
    contrib = fetch_contribution_data(username)
    days = contrib["days"]
    weeks_raw = contrib["weeks"]

    # 2. Languages
    languages = fetch_languages(username)

    # 3. Derived stats
    streaks = compute_streaks(days)
    activity = compute_activity_stats(days)

    # 4. Generate SVGs
    generate_sparkline(days, os.path.join(ASSETS_DIR, "sparkline.svg"))
    generate_streaks_svg(streaks, os.path.join(ASSETS_DIR, "streaks.svg"))
    generate_languages_svg(languages, os.path.join(ASSETS_DIR, "languages.svg"))
    generate_calendar_svg(weeks_raw, os.path.join(ASSETS_DIR, "calendar.svg"))

    metrics = {
        "username": username,
        "total_contributions": contrib["total"],
        "current_streak": streaks["current"],
        "longest_streak": streaks["longest"],
        "active_days": activity["active_days"],
        "best_week": activity["best_week"],
        "top_language": languages[0]["name"] if languages else "N/A",
        "languages": languages,
    }

    print(f"Metrics: {json.dumps(metrics, indent=2)}")
    return metrics


# ── CLI ────────────────────────────────────────────────────────
if __name__ == "__main__":
    fetch_and_generate()
