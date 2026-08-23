# Local Setup & Testing Guide

This document explains how to test the GitHub Profile README generator locally before pushing to GitHub.

---

## Prerequisites

- **Python 3.11+** installed
- **Git** installed
- A **GitHub Personal Access Token** (classic) with these scopes:
  - `read:user` — read your profile data
  - `repo` — access public repo metadata and language stats

---

## Step 1: Create a Personal Access Token

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Give it a descriptive name (e.g., `profile-readme-local`)
4. Select scopes: `read:user`, `repo`
5. Click **Generate token** and copy it immediately

---

## Step 2: Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_USERNAME.git
cd YOUR_USERNAME
```

Set your token as an environment variable:

**Linux/macOS (Bash/Zsh):**
```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

**Windows (PowerShell):**
```powershell
$env:GITHUB_TOKEN = "ghp_your_token_here"
```

**Windows (CMD):**
```cmd
set GITHUB_TOKEN=ghp_your_token_here
```

Optionally set your username (auto-detected from token if omitted):
```bash
export GITHUB_USERNAME="your-github-username"
```

---

## Step 3: Add Your Avatar

Place a headshot image at:

```
assets/avatar.png
```

**Tips:**
- Square aspect ratio works best (e.g., 400×400)
- Higher contrast images produce better ASCII art
- The script will gracefully generate a placeholder if the file is missing

---

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `Pillow` — image processing for ASCII art generation
- `requests` — HTTP client for GitHub API

---

## Step 5: Run the Builder

```bash
python scripts/build_readme.py
```

Expected output:
```
============================================================
  GitHub Profile README Builder
============================================================

[1/3] Generating ASCII portrait…
Converting assets/avatar.png → ASCII art (80 cols)…
Portrait SVG written to assets/portrait.svg

[2/3] Fetching GitHub metrics & generating SVGs…
Fetching metrics for @your-username…
Sparkline SVG → assets/sparkline.svg
Streaks SVG → assets/streaks.svg
Languages SVG → assets/languages.svg
Calendar SVG → assets/calendar.svg

[3/3] Building README.md…

✓ README.md written to README.md
============================================================
```

---

## Step 6: Preview

Open the generated files to verify:

| File | Purpose |
|---|---|
| `README.md` | Final rendered profile — open in a Markdown previewer |
| `assets/portrait.svg` | ASCII art portrait |
| `assets/sparkline.svg` | 52-week contribution sparkline |
| `assets/streaks.svg` | Current & longest streak card |
| `assets/languages.svg` | Language breakdown bar chart |
| `assets/calendar.svg` | Yearly contribution calendar |

Open SVGs directly in your browser to inspect rendering.

---

## Step 7: Customize

### Static content
Edit `templates/README.template.md` to personalize:
- **About section** — your bio and social links
- **Stack** — your actual tech stack
- **Projects** — your featured repositories

### Dynamic placeholders
These are auto-populated by the build script:

| Placeholder | Description |
|---|---|
| `{{USERNAME}}` | GitHub username |
| `{{TOTAL_CONTRIBUTIONS}}` | Yearly contribution count |
| `{{CURRENT_STREAK}}` | Current daily streak |
| `{{LONGEST_STREAK}}` | Longest daily streak |
| `{{ACTIVE_DAYS}}` | Days with ≥1 contribution |
| `{{BEST_WEEK}}` | Highest 7-day contribution total |
| `{{TOP_LANGUAGE}}` | Most-used language by bytes |
| `{{YEAR}}` | Current year |
| `{{LAST_UPDATED}}` | Timestamp of last generation |

### ASCII art tuning
In `scripts/ascii_generator.py`, adjust:
- `OUTPUT_WIDTH` — character columns (default: 80)
- `CHAR_RAMP` — character set for luminance mapping
- `FONT_SIZE` / `LINE_HEIGHT` — SVG text sizing

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ERROR: GITHUB_TOKEN environment variable is required` | Set the `GITHUB_TOKEN` env var |
| `WARNING: avatar.png not found` | Place an image at `assets/avatar.png` |
| Rate limit errors | Wait for reset or use a token with higher limits |
| Empty/missing SVGs | Check the console output for GraphQL error messages |
| `ModuleNotFoundError: Pillow` | Run `pip install -r requirements.txt` |

---

## Pushing to GitHub

Once verified locally:

```bash
git add .
git commit -m "feat: initial profile README with auto-generated SVGs"
git push origin main
```

The GitHub Actions workflow will then run nightly to keep your profile fresh.
