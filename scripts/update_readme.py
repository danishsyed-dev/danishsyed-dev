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


# Shields.io badge config: (background color, logo name)
TECH_BADGE_MAP = {
    "Python": ("3670A0", "python", "ffdd54"),
    "JavaScript": ("323330", "javascript", "F7DF1E"),
    "TypeScript": ("007ACC", "typescript", "white"),
    "HTML": ("E34F26", "html5", "white"),
    "CSS": ("1572B6", "css3", "white"),
    "C++": ("00599C", "cplusplus", "white"),
    "C": ("00599C", "c", "white"),
    "R": ("276DC3", "r", "white"),
    "Jupyter Notebook": ("F37626", "jupyter", "white"),
    "TensorFlow": ("FF6F00", "tensorflow", "white"),
    "PyTorch": ("EE4C2C", "pytorch", "white"),
    "scikit-learn": ("F7931E", "scikit-learn", "white"),
    "Pandas": ("150458", "pandas", "white"),
    "NumPy": ("013243", "numpy", "white"),
    "Flask": ("000000", "flask", "white"),
    "Django": ("092E20", "django", "white"),
    "FastAPI": ("009688", "fastapi", "white"),
    "React": ("20232a", "react", "61DAFB"),
    "Node.js": ("339933", "node.js", "white"),
    "MLflow": ("0194E2", "mlflow", "white"),
    "LangChain": ("1C3C3C", "langchain", "white"),
    "OpenCV": ("5C3EE8", "opencv", "white"),
    "Arduino": ("00979D", "arduino", "white"),
    "Docker": ("2496ED", "docker", "white"),
    "AWS": ("FF9900", "amazonaws", "white"),
    "MongoDB": ("47A248", "mongodb", "white"),
    "PostgreSQL": ("316192", "postgresql", "white"),
    "CNN": ("FF6F00", "tensorflow", "white"),
    "Deep Learning": ("EE4C2C", "pytorch", "white"),
    "NLP": ("4EA94B", "spacy", "white"),
    "IoT": ("010101", "internetofthings", "white"),
    "Git": ("F05033", "git", "white"),
    "Code": ("555555", "code", "white"),
}


def build_tech_badge(tech_name):
    """Build a shields.io badge for a technology."""
    label = tech_name.replace("-", "--").replace(" ", "%20")
    if tech_name in TECH_BADGE_MAP:
        bg, logo, logo_color = TECH_BADGE_MAP[tech_name]
        return (
            f'![{tech_name}](https://img.shields.io/badge/{label}-{bg}?style=flat'
            f'&logo={logo}&logoColor={logo_color})'
        )
    # Fallback: grey badge, no logo
    return (
        f'![{tech_name}](https://img.shields.io/badge/{label}-555555?style=flat)'
    )


def build_project_card(display_name, description, tech, emoji, url):
    """Build a card for a single project using markdown inside HTML td."""
    badges = " ".join(build_tech_badge(t) for t in tech)
    # Blank lines around content inside <td> are required for GitHub
    # to parse the inner content as markdown
    return (
        f'<td width="50%">\n'
        f'\n'
        f'### {emoji} [{display_name}]({url})\n'
        f'\n'
        f'>{description}\n'
        f'\n'
        f'{badges}\n'
        f'\n'
        f'</td>'
    )


def generate_projects_table(config, repos):
    """Generate the full projects section as HTML cards."""
    all_projects = []

    pinned_names = set(entry["name"] for entry in config.get("pinned", []))

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
            all_projects.append(
                build_project_card(
                    display_name=display_name,
                    description=description,
                    tech=languages,
                    emoji=emoji,
                    url=url,
                )
            )
            added += 1

    # --- Pinned repos (manual entries, shown after recent) ---
    for entry in config.get("pinned", []):
        name = entry["name"]
        url = f"https://github.com/{GITHUB_USERNAME}/{name}"
        all_projects.append(
            build_project_card(
                display_name=entry.get("display_name", name),
                description=entry.get("description", ""),
                tech=entry.get("tech", []),
                emoji=entry.get("emoji", FALLBACK_EMOJI),
                url=url,
            )
        )

    # --- Build 2-column HTML table ---
    lines = [
        "## 🚀 Featured Projects",
        "",
        '<div align="center">',
        '<table>',
    ]

    for i in range(0, len(all_projects), 2):
        lines.append("<tr>")
        lines.append(all_projects[i])
        if i + 1 < len(all_projects):
            lines.append(all_projects[i + 1])
        else:
            lines.append('<td width="50%"></td>')
        lines.append("</tr>")

    lines.append("</table>")
    lines.append("</div>")

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
