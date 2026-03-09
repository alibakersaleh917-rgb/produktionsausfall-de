import os
import re
import json
import time
import random
import datetime
import argparse
from pathlib import Path
from difflib import SequenceMatcher

from domain_config import DEFAULT_CONFIG, load_domain_config

OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
UNSPLASH_KEY = os.environ.get("UNSPLASH_KEY", "")

WRITER_MODEL = "google/gemini-2.0-flash-001"
REVIEW_MODEL = "mistralai/mistral-small-24b-instruct-2501"

CONFIG_PATH = Path(os.environ.get("DOMAIN_CONFIG_PATH", "data/domain.yaml"))

CONFIG = load_domain_config(CONFIG_PATH)

def language_prompt_config(language_code: str) -> tuple[str, str]:
    code = (language_code or "de").lower()
    if code.startswith("de"):
        return "Deutsch", "deutscher"
    if code.startswith("en"):
        return "English", "english"
    if code.startswith("fr"):
        return "Français", "français"
    if code.startswith("es"):
        return "Español", "español"
    return language_code or "Deutsch", "international"


def get_brand_positioning() -> str:
    return CONFIG.get("brand_positioning") or (
        f"{CONFIG['brand_name']} positioniert sich in {CONFIG['geo']} "
        f"für {CONFIG['niche']} mit Fokus auf {CONFIG['audience']}."
    )


POSTS_DIR = Path("content/posts")
IMAGES_DIR = Path("static/images")
TODAY = datetime.datetime.utcnow().strftime("%Y-%m-%d")
KEYWORD = random.choice(CONFIG["keywords"])


def call_openrouter(prompt: str, model: str, max_tokens: int = 2400) -> str:
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_KEY is required")

    import requests

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        timeout=180,
    )

    if response.status_code != 200:
        raise Exception(f"{response.status_code}: {response.text[:500]}")

    return response.json()["choices"][0]["message"]["content"].strip()


def slugify(text: str) -> str:
    text = text.lower().strip()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def extract_markdown_block(text: str) -> str:
    match = re.search(r"```(?:markdown|md)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    else:
        text = text.strip()

    if "---" in text:
        text = text[text.find("---"):].strip()

    return text


def has_valid_frontmatter(article: str) -> bool:
    if not article.startswith("---"):
        return False

    parts = article.split("---", 2)
    if len(parts) < 3:
        return False

    fm = parts[1]
    required = ["title:", "date:", "description:", "keywords:"]
    return all(field in fm for field in required)


def parse_frontmatter(article: str):
    parts = article.split("---", 2)
    if len(parts) < 3:
        return None, None

    frontmatter = parts[1].strip()
    body = parts[2].strip()

    def grab(pattern: str, default: str = "") -> str:
        m = re.search(pattern, frontmatter, re.MULTILINE)
        return m.group(1).strip() if m else default

    title = grab(r'^title:\s*["\']?(.*?)["\']?$')
    description = grab(r'^description:\s*["\']?(.*?)["\']?$')
    date_value = grab(r'^date:\s*["\']?(.*?)["\']?$')
    keywords_line = grab(r"^keywords:\s*(.*?)$")
    image_line = grab(r'^image:\s*["\']?(.*?)["\']?$')

    return {
        "title": title,
        "description": description,
        "date": date_value,
        "keywords_line": keywords_line,
        "image": image_line,
    }, body


def normalize_keywords_line(keywords_line: str, fallback_keyword: str) -> str:
    if not keywords_line:
        return f'["{fallback_keyword}"]'

    keywords_line = keywords_line.strip()

    if keywords_line.startswith("[") and keywords_line.endswith("]"):
        return keywords_line

    return f'["{fallback_keyword}"]'


def _score_unsplash_candidate(candidate: dict, keyword: str) -> int:
    score = 0

    location = candidate.get("location") or {}
    country = (location.get("country") or "").lower()
    city = (location.get("city") or "").lower()

    geo_tokens = [t.lower() for t in re.split(r"[\s,;/]+", str(CONFIG.get("geo", ""))) if t]

    if country and any(token in country for token in geo_tokens):
        score += 25

    title_blob = " ".join(
        [
            candidate.get("description") or "",
            candidate.get("alt_description") or "",
            keyword,
            CONFIG.get("niche", ""),
            CONFIG.get("seo_keyword_hints", ""),
        ]
    ).lower()

    relevance_tokens = [
        token.lower()
        for token in re.split(r"[\s,;/]+", f"{CONFIG.get('niche','')} {CONFIG.get('seo_keyword_hints','')}")
        if len(token) > 2
    ]
    if any(token in title_blob for token in relevance_tokens):
        score += 20

    score += int(candidate.get("width", 0) >= 1600)
    score += int(candidate.get("height", 0) >= 900)

    return score


def _unsplash_random_candidates(query: str, count: int = 8):
    if not UNSPLASH_KEY:
        raise RuntimeError("UNSPLASH_KEY is required")

    import requests

    response = requests.get(
        "https://api.unsplash.com/photos/random",
        params={
            "query": query,
            "orientation": "landscape",
            "content_filter": "high",
            "count": count,
            "client_id": UNSPLASH_KEY,
        },
        timeout=60,
    )

    if response.status_code == 404:
        return []

    if response.status_code != 200:
        raise Exception(f"Unsplash random error: {response.status_code} {response.text[:300]}")

    data = response.json()
    return data if isinstance(data, list) else [data]


def _unsplash_search_candidates(query: str, per_page: int = 20):
    if not UNSPLASH_KEY:
        raise RuntimeError("UNSPLASH_KEY is required")

    import requests

    response = requests.get(
        "https://api.unsplash.com/search/photos",
        params={
            "query": query,
            "orientation": "landscape",
            "content_filter": "high",
            "per_page": per_page,
            "client_id": UNSPLASH_KEY,
        },
        timeout=60,
    )

    if response.status_code == 404:
        return []

    if response.status_code != 200:
        raise Exception(f"Unsplash search error: {response.status_code} {response.text[:300]}")

    data = response.json()
    return data.get("results", [])


def fetch_unsplash_image(keyword: str, slug: str) -> str:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    image_hint = CONFIG.get("image_style_hints", "")
    query_seed = [hint.strip() for hint in str(image_hint).split(";") if hint.strip()]

    geo = CONFIG.get("geo", "")
    niche = CONFIG.get("niche", "")

    queries = [f"{keyword} {hint}" for hint in query_seed]
    queries.extend([
        f"{keyword} {niche} {geo}",
        f"{keyword} {geo}",
        f"{niche} {geo}",
        f"{keyword} consultation",
        f"{niche} professional office",
    ])

    candidates = []
    for query in queries:
        try:
            random_hits = _unsplash_random_candidates(query, count=8)
            candidates.extend(random_hits)

            if len(candidates) < 3:
                search_hits = _unsplash_search_candidates(query, per_page=20)
                candidates.extend(search_hits)

            if candidates:
                break
        except Exception as err:
            print(f"Unsplash query failed ({query}): {err}")
            continue

    if not candidates:
        raise Exception("Unsplash returned no image candidates for all fallback queries")

    best = max(candidates, key=lambda c: _score_unsplash_candidate(c, keyword))
    urls = best.get("urls") or {}
    image_url = urls.get("regular") or urls.get("full") or urls.get("small")

    if not image_url:
        raise Exception("Unsplash image URL missing")

    import requests

    image_response = requests.get(image_url, stream=True, timeout=60)
    if image_response.status_code != 200:
        raise Exception("Failed to download image from Unsplash")

    filename = f"{TODAY}-{slug}.jpg"
    filepath = IMAGES_DIR / filename

    with open(filepath, "wb") as f:
        for chunk in image_response.iter_content(8192):
            f.write(chunk)

    return f"/images/{filename}"


def strip_junk_prefix(body: str) -> str:
    junk_prefixes = [
        "hier ist der optimierte artikel",
        "hier ist der überarbeitete artikel",
        "hier ist die optimierte version",
        "hier ist die verbesserte version",
        "hier ist der verbesserte artikel",
        "improved article",
        "optimized article",
        "überarbeiteter artikel",
    ]

    body_clean = body.strip()
    body_lower = body_clean.lower()

    for prefix in junk_prefixes:
        if body_lower.startswith(prefix):
            split_pos = body_clean.find("\n")
            if split_pos != -1:
                body_clean = body_clean[split_pos:].strip()
            break

    return body_clean


def strip_frontmatter_lines_from_body(body: str) -> str:
    body = re.sub(r'^title:\s*.*$', '', body, flags=re.MULTILINE)
    body = re.sub(r'^date:\s*.*$', '', body, flags=re.MULTILINE)
    body = re.sub(r'^description:\s*.*$', '', body, flags=re.MULTILINE)
    body = re.sub(r'^keywords:\s*.*$', '', body, flags=re.MULTILINE)
    return body


def ensure_domain_cta(body: str) -> str:
    cta_phrase = CONFIG.get("brand_name") or CONFIG["domain"]
    if cta_phrase.lower() in body.lower():
        return body.strip()

    cta_text = CONFIG.get("article_cta") or (
        "Wenn Sie eine Marke für Legal-Tech, digitale Rechtsberatung oder "
        "Mandantenvermittlung in Deutschland aufbauen möchten, kann "
        f"**{cta_phrase}** eine starke und einprägsame Domain für Ihr Projekt sein."
    )
    cta = "\n\n---\n\n" + cta_text
    return body.strip() + cta


def normalize_article(article: str, image_path: str = "") -> str:
    article = extract_markdown_block(article)

    if "---" not in article:
        raise ValueError("No frontmatter found")

    article = article[article.find("---"):].strip()
    parts = article.split("---", 2)

    if len(parts) < 3:
        raise ValueError("Invalid frontmatter structure")

    raw_frontmatter = parts[1].strip()
    body = parts[2].strip()

    def grab(pattern: str, default: str = "") -> str:
        m = re.search(pattern, raw_frontmatter, re.MULTILINE)
        return m.group(1).strip() if m else default

    title = grab(r'^title:\s*["\']?(.*?)["\']?$') or f"{KEYWORD} – Ratgeber und Tipps"
    description = grab(r'^description:\s*["\']?(.*?)["\']?$') or f"Erfahren Sie mehr über {KEYWORD} auf {CONFIG['domain']}."
    keywords_line = grab(r'^keywords:\s*(.*?)$')
    keywords_line = normalize_keywords_line(keywords_line, KEYWORD)

    body = strip_junk_prefix(body)
    body = strip_frontmatter_lines_from_body(body)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    body = ensure_domain_cta(body)

    image_block = f'image: "{image_path}"\n' if image_path else ""

    clean = f"""---
title: "{title}"
date: "{TODAY}"
description: "{description}"
keywords: {keywords_line}
{image_block}---

{body}
"""
    return clean


def keyword_count(text: str, keyword: str) -> int:
    return text.lower().count(keyword.lower())


def is_duplicate(new_article: str, threshold: float = 0.70) -> bool:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    for path in POSTS_DIR.glob("*.md"):
        old = path.read_text(encoding="utf-8", errors="ignore")
        ratio = SequenceMatcher(None, old, new_article).ratio()
        if ratio > threshold:
            return True

    return False


def generate_prompt(keyword: str) -> str:
    language_name, language_style = language_prompt_config(CONFIG.get("language", "de"))
    brand_positioning = get_brand_positioning()
    seo_hints = CONFIG.get("seo_keyword_hints") or ""

    return f"""
Du bist ein professioneller {language_style} SEO-Content-Writer mit Fokus auf hochwertige, natürlich klingende Fachartikel.

Deine Aufgabe:
Schreibe einen starken SEO-Artikel für die Domain {CONFIG["domain"]}.

WICHTIGE REGELN:
- Schreibe ausschließlich in {language_name}.
- Gib nur reines Markdown zurück.
- Keine Erklärungen vor oder nach dem Artikel.
- Beginne direkt mit gültigem YAML-Frontmatter.
- Verwende exakt dieses Datumsformat: "{TODAY}".
- Der Text muss natürlich, vertrauenswürdig und menschlich klingen.
- Keine generischen KI-Formulierungen und kein unnötiger Fülltext.

KONTEXT:
- Domain: {CONFIG["domain"]}
- Marke: {CONFIG["brand_name"]}
- Nische: {CONFIG["niche"]}
- Region: {CONFIG["geo"]}
- Sprache: {language_name}
- Zielgruppe: {CONFIG["audience"]}
- Brand Positioning: {brand_positioning}
- Hauptkeyword: {keyword}
- SEO Keyword-Hinweise: {seo_hints}

SEO-ZIEL:
Der Artikel soll für Suchanfragen rund um das Hauptkeyword ranken und gleichzeitig zur Nische, Zielgruppe und Markenpositionierung passen.

ANFORDERUNGEN:
- Länge: 1100 bis 1400 Wörter
- Struktur:
  - 1 klare H1
  - 4 bis 6 sinnvolle H2-Abschnitte
  - kurze, starke Einleitung
  - prägnantes Fazit
- Verwende das Hauptkeyword natürlich etwa 3 bis 5 Mal.
- Nutze sinnvolle semantische Begriffe und verwandte Suchintentionen.
- Schreibe im Stil: {CONFIG["article_tone"]}.
- Vermeide Wiederholungen.
- Gib konkrete, praktische Informationen statt leerer Allgemeinplätze.
- Der Artikel darf nicht mit Meta-Kommentaren beginnen.
- Schreibe keinen Satz wie "Hier ist der Artikel" oder ähnliche Hinweise.

WICHTIG FÜR DIE DOMAIN-STRATEGIE:
Baue am Ende des Artikels eine kurze und natürliche Erwähnung ein, dass die Domain {CONFIG["domain"]} für die Zielgruppe in dieser Nische eine interessante Marke sein kann.

FORMAT:
---
title: "..."
date: "{TODAY}"
description: "..."
keywords: ["{keyword}"]
---

# Titel

Artikeltext...
""".strip()


def review_prompt(article: str, keyword: str) -> str:
    language_name, _ = language_prompt_config(CONFIG.get("language", "de"))
    return f"""
Du bist ein strenger SEO-Editor.

Überarbeite den folgenden Artikel.

REGELN:
- Behalte YAML-Frontmatter.
- Behalte die Sprache: {language_name}.
- Gib nur Markdown zurück.
- Verbessere Lesbarkeit, Klarheit und Natürlichkeit.
- Entferne Füllsätze und typische KI-Formulierungen.
- Entferne jede Meta-Erklärung wie "Hier ist der optimierte Artikel".
- Es darf kein YAML-Text doppelt im Fließtext erscheinen.
- Stelle sicher, dass das Hauptkeyword "{keyword}" natürlich ungefähr 3 bis 5 Mal vorkommt.
- Erhalte die Struktur des Artikels.
- Ändere das Datum nicht.
- Lasse den Text professionell und glaubwürdig wirken.
- Achte darauf, dass der Schluss die Domain natürlich und dezent erwähnt.

ARTIKEL:
{article}
""".strip()


def save_article(article: str, title: str) -> Path:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(title) or f"artikel-{random.randint(1000, 9999)}"
    filename = POSTS_DIR / f"{TODAY}-{slug}.md"
    filename.write_text(article, encoding="utf-8")
    return filename



def run_dry_run(keyword: str):
    print("=== DRY RUN ===")
    print(f"Config path: {CONFIG_PATH}")
    print("Domain:", CONFIG.get("domain"))
    print("Brand:", CONFIG.get("brand_name"))
    print("Niche:", CONFIG.get("niche"))
    print("Geo:", CONFIG.get("geo"))
    print("Language:", CONFIG.get("language"))
    print("Audience:", CONFIG.get("audience"))
    print("Tone:", CONFIG.get("article_tone"))
    print("Keyword:", keyword)
    print("\n--- Prompt Preview ---\n")
    print(generate_prompt(keyword))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print config/prompt and exit")
    parser.add_argument("--keyword", default=None, help="Override random keyword")
    return parser.parse_args()

def main():
    args = parse_args()
    selected_keyword = args.keyword or KEYWORD

    if args.dry_run:
        run_dry_run(selected_keyword)
        return

    print(f"Keyword selected: {selected_keyword}")

    for attempt in range(3):
        try:
            draft = call_openrouter(generate_prompt(selected_keyword), WRITER_MODEL)
            draft = normalize_article(draft)

            if not has_valid_frontmatter(draft):
                raise ValueError("Draft frontmatter invalid")

            reviewed = call_openrouter(review_prompt(draft, selected_keyword), REVIEW_MODEL)
            reviewed = normalize_article(reviewed)

            if not has_valid_frontmatter(reviewed):
                print("Reviewed version invalid, using draft.")
                reviewed = draft

            count = keyword_count(reviewed, selected_keyword)
            if count < 2 or count > 6:
                print(f"Keyword count out of preferred range: {count}")

            if is_duplicate(reviewed):
                raise ValueError("Generated article is too similar to an existing post")

            parsed, _ = parse_frontmatter(reviewed)
            title = parsed["title"] if parsed else f"artikel-{random.randint(1000, 9999)}"
            slug = slugify(title) or f"artikel-{random.randint(1000, 9999)}"

            image_path = ""
            try:
                image_path = fetch_unsplash_image(selected_keyword, slug)
            except Exception as image_err:
                print(f"Image fetch skipped: {image_err}")

            reviewed = normalize_article(reviewed, image_path=image_path)

            saved_path = save_article(reviewed, title)
            print(f"Saved: {saved_path}")
            if image_path:
                print(f"Image: {image_path}")
            return

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)

    raise Exception("Failed after 3 attempts")


if __name__ == "__main__":
    main()
