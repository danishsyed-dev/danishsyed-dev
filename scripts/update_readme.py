"""
Auto-update the Featured Projects section of README.md.

This script:
1. Reads pinned repos from featured_repos.json (manual entries)
2. Fetches recent public repos from GitHub API (auto entries)
3. Merges them (pinned first, then recent — no duplicates)
4. Regenerates the table between <!-- PROJECTS:START --> and <!-- PROJECTS:END -->
"""

import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime


GITHUB_USERNAME = "danishsyed-dev"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(REPO_ROOT, "README.md")
CONFIG_PATH = os.path.join(REPO_ROOT, "featured_repos.json")

# Markers in README.md
START_MARKER = "<!-- PROJECTS:START -->"
END_MARKER = "<!-- PROJECTS:END -->"

# Default emoji for auto-added repos
AUTO_EMOJI = "📦"

# Language-to-tech mapping for auto-detected repos
LANGUAGE_MAP = {
    "Python": ["Python"],
    "JavaScript": ["JavaScript"],
    "TypeScript": ["TypeScript"],
    "Jupyter Notebook": ["Python", "Jupyter"],
    "HTML": ["HTML", "CSS"],
    "C++": ["C++"],
    "C": ["C"],
    "Java": ["Java"],
    "Rust": ["Rust"],
    "Go": ["Go"],
    "R": ["R"],
}


def fetch_repos():
    """Fetch all public repos from GitHub API."""
    repos = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{GITHUB_USERNAME}/repos"
            f"?type=public&sort=pushed&direction=desc&per_page=100&page={page}"
        )
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "readme-updater")

        # Use GitHub token if available (avoids rate limits)
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            req.add_header("Authorization", f"token {token}")

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if not data:
                    break
                repos.extend(data)
                page += 1
        except urllib.error.HTTPError as e:
            print(f"⚠️  GitHub API error: {e.code} - {e.reason}")
            break

    return repos


def load_config():
    """Load the featured repos config file."""
    if not os.path.exists(CONFIG_PATH):
        print("⚠️  featured_repos.json not found, using empty config")
        return {"pinned": [], "auto_add_recent": True, "max_recent": 3, "exclude": []}

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_table_row(name, display_name, description, tech, emoji, url):
    """Build a single markdown table row."""
    tech_str = " ".join(f"`{t}`" for t in tech)
    return (
        f"| {emoji} [**{display_name}**]({url}) "
        f"| {description} "
        f"| {tech_str} |"
    )


def generate_projects_table(config, repos):
    """Generate the full projects markdown table."""
    lines = [
        "## 🚀 Featured Projects",
        "",
        "| Project | Description | Tech |",
        "|:--------|:------------|:-----|",
    ]

    pinned_names = set()

    # --- Pinned repos (manual entries, always shown first) ---
    for entry in config.get("pinned", []):
        name = entry["name"]
        pinned_names.add(name)
        url = f"https://github.com/{GITHUB_USERNAME}/{name}"
        lines.append(
            build_table_row(
                name=name,
                display_name=entry.get("display_name", name),
                description=entry.get("description", ""),
                tech=entry.get("tech", []),
                emoji=entry.get("emoji", AUTO_EMOJI),
                url=url,
            )
        )

    # --- Auto-add recent repos ---
    if config.get("auto_add_recent", True):
        exclude = set(config.get("exclude", []))
        max_recent = config.get("max_recent", 3)
        added = 0

        for repo in repos:
            if added >= max_recent:
                break

            name = repo["name"]

            # Skip if already pinned, excluded, forked, or private
            if name in pinned_names or name in exclude:
                continue
            if repo.get("fork", False) or repo.get("private", False):
                continue

            # Detect tech from language
            language = repo.get("language") or "Unknown"
            tech = LANGUAGE_MAP.get(language, [language])

            # Use repo description or generate one
            description = repo.get("description") or f"Recently updated {language} project"
            display_name = name.replace("-", " ").replace("_", " ").title()

            url = repo["html_url"]
            lines.append(
                build_table_row(
                    name=name,
                    display_name=display_name,
                    description=description,
                    tech=tech,
                    emoji=AUTO_EMOJI,
                    url=url,
                )
            )
            pinned_names.add(name)
            added += 1

    return "\n".join(lines)


def update_readme(new_section):
    """Replace content between markers in README.md."""
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )

    if not pattern.search(content):
        print("❌ Markers not found in README.md!")
        print(f"   Add {START_MARKER} and {END_MARKER} around the projects section.")
        return False

    replacement = f"{START_MARKER}\n{new_section}\n{END_MARKER}"
    updated = pattern.sub(replacement, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    return True


def main():
    print("📦 Fetching repos from GitHub...")
    repos = fetch_repos()
    print(f"   Found {len(repos)} public repos")

    print("📋 Loading config...")
    config = load_config()
    print(f"   {len(config.get('pinned', []))} pinned repos")

    print("🔨 Generating projects table...")
    table = generate_projects_table(config, repos)

    print("✏️  Updating README.md...")
    if update_readme(table):
        print("✅ README.md updated successfully!")
    else:
        print("❌ Failed to update README.md")
        exit(1)


if __name__ == "__main__":
    main()
