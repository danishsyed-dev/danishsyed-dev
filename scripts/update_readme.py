"""
Auto-update the Featured Projects section of README.md.

This script:
1. Reads pinned repos from featured_repos.json (manual entries)
2. Fetches recent public repos from GitHub API (auto entries)
3. For auto repos: pulls description, emoji from README, languages from API
4. Merges them (pinned first, then recent — no duplicates)
5. Regenerates the table between <!-- PROJECTS:START --> and <!-- PROJECTS:END -->
"""

import json
import os
import re
import urllib.request
import urllib.error
import base64


GITHUB_USERNAME = "danishsyed-dev"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(REPO_ROOT, "README.md")
CONFIG_PATH = os.path.join(REPO_ROOT, "featured_repos.json")

# Markers in README.md
START_MARKER = "<!-- PROJECTS:START -->"
END_MARKER = "<!-- PROJECTS:END -->"

# Fallback emoji for auto-added repos when none found in README
FALLBACK_EMOJI = "📂"

# Common domain-specific emoji mapping
TOPIC_EMOJI_MAP = {
    "machine-learning": "🤖",
    "deep-learning": "🧠",
    "data-science": "📊",
    "web": "🌐",
    "api": "🔌",
    "iot": "💡",
    "nlp": "📝",
    "computer-vision": "👁️",
    "flask": "🌶️",
    "django": "🎸",
    "prediction": "📈",
    "healthcare": "🏥",
    "finance": "💰",
    "game": "🎮",
    "bot": "🤖",
    "scraper": "🕷️",
    "automation": "⚙️",
    "analytics": "📊",
}


def github_request(url):
    """Make an authenticated GitHub API request."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "readme-updater")

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"token {token}")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  ⚠️  API error for {url}: {e.code}")
        return None


def fetch_repos():
    """Fetch all public repos from GitHub API, sorted by most recently pushed."""
    repos = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{GITHUB_USERNAME}/repos"
            f"?type=public&sort=pushed&direction=desc&per_page=100&page={page}"
        )
        data = github_request(url)
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    return repos


def fetch_repo_languages(repo_name):
    """Fetch languages used in a repo from GitHub API."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/languages"
    data = github_request(url)
    if data:
        # Sort by bytes of code (most used first), take top 3
        sorted_langs = sorted(data.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, _ in sorted_langs[:3]]
    return []


def extract_emoji_from_readme(repo_name):
    """Fetch the repo's README and extract the first emoji from the heading."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/readme"
    data = github_request(url)
    if not data or "content" not in data:
        return None

    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    except Exception:
        return None

    # Look for emoji in the first heading (# Title or ## Title)
    for line in content.split("\n")[:10]:
        line = line.strip()
        if line.startswith("#"):
            # Remove markdown heading markers
            text = re.sub(r"^#+\s*", "", line)
            # Extract first emoji (Unicode emoji ranges)
            emoji_match = re.search(
                r"[\U0001F300-\U0001F9FF\U00002700-\U000027BF\U0001FA00-\U0001FAFF"
                r"\U00002600-\U000026FF\U0000FE00-\U0000FEFF\U0001F000-\U0001F02F"
                r"\U0001F600-\U0001F64F\U0001F680-\U0001F6FF]",
                text,
            )
            if emoji_match:
                return emoji_match.group(0)

    return None


def guess_emoji_from_name(repo_name, topics=None):
    """Guess an appropriate emoji based on repo name and topics."""
    name_lower = repo_name.lower().replace("-", " ").replace("_", " ")

    # Check topics first
    if topics:
        for topic in topics:
            if topic in TOPIC_EMOJI_MAP:
                return TOPIC_EMOJI_MAP[topic]

    # Check name keywords
    for keyword, emoji in TOPIC_EMOJI_MAP.items():
        if keyword in name_lower:
            return emoji

    return FALLBACK_EMOJI


def load_config():
    """Load the featured repos config file."""
    if not os.path.exists(CONFIG_PATH):
        print("⚠️  featured_repos.json not found, using empty config")
        return {"pinned": [], "auto_add_recent": True, "max_recent": 5, "exclude": []}

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_table_row(display_name, description, tech, emoji, url):
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

    pinned_names = set(entry["name"] for entry in config.get("pinned", []))
    recent_lines = []

    # --- Auto-add recent repos first (latest projects on top) ---
    if config.get("auto_add_recent", True):
        exclude = set(config.get("exclude", []))
        max_recent = config.get("max_recent", 5)
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

            print(f"  🔍 Auto-adding: {name}")

            # --- Get real description from GitHub ---
            description = repo.get("description")
            if not description:
                description = f"{name.replace('-', ' ').replace('_', ' ').title()} project"

            # --- Get emoji from README header, fallback to name/topic guess ---
            emoji = extract_emoji_from_readme(name)
            if not emoji:
                topics = repo.get("topics", [])
                emoji = guess_emoji_from_name(name, topics)
            print(f"    Emoji: {emoji}")

            # --- Get languages from GitHub API ---
            languages = fetch_repo_languages(name)
            if not languages:
                primary = repo.get("language")
                languages = [primary] if primary else ["Code"]
            print(f"    Languages: {languages}")

            # Clean up display name
            display_name = name.replace("-", " ").replace("_", " ").title()

            url = repo["html_url"]
            recent_lines.append(
                build_table_row(
                    display_name=display_name,
                    description=description,
                    tech=languages,
                    emoji=emoji,
                    url=url,
                )
            )
            added += 1

    # Add recent repos first (latest on top)
    lines.extend(recent_lines)

    # --- Pinned repos (manual entries, shown after recent) ---
    for entry in config.get("pinned", []):
        name = entry["name"]
        url = f"https://github.com/{GITHUB_USERNAME}/{name}"
        lines.append(
            build_table_row(
                display_name=entry.get("display_name", name),
                description=entry.get("description", ""),
                tech=entry.get("tech", []),
                emoji=entry.get("emoji", FALLBACK_EMOJI),
                url=url,
            )
        )

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
