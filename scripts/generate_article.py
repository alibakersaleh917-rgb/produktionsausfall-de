from google import genai
from google.genai import types
import requests, os, datetime, random, re, shutil, time
from difflib import SequenceMatcher

# --- API Keys ---
FLASH_KEYS = [
    os.environ["GEMINI_KEY_1"],
    os.environ["GEMINI_KEY_2"],
    os.environ["GEMINI_KEY_3"],
    os.environ["GEMINI_KEY_4"],
    os.environ["GEMINI_KEY_5"],
    os.environ["GEMINI_KEY_6"],
]

# --- Domain Config ---
CONFIG = {
    "domain":    "anwaltsagent.de",
    "niche":     "Rechtsberatung / Legal Matching",
    "geo":       "Deutschland",
    "language":  "German",
    "audience":  "Unternehmen und Privatpersonen auf der Suche nach einem Anwalt",
    "keywords": [
        "Anwalt finden Deutschland",
        "Rechtsanwalt beauftragen online",
        "Anwaltssuche Deutschland",
        "Anwalt für Unternehmen Deutschland",
        "günstige Rechtsberatung online",
        "Anwalt Erstberatung Kosten",
        "bester Anwalt Deutschland finden",
        "Rechtsberatung online Deutschland",
    ]
}

date_str = datetime.date.today().isoformat()
keyword  = random.choice(CONFIG["keywords"])

# --- Fallback Generator ---
def generate_with_fallback(prompt):
    for key in FLASH_KEYS:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-1.5-flash-latest",
                contents=prompt
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"Key exhausted, trying next...")
                continue
            raise e
    raise Exception("All API keys exhausted")

# --- Prompts ---
def generation_prompt():
    return f"""You are an expert SEO content writer.
Write a German blog article for the website {CONFIG['domain']}.
Write ONLY in German. Do not mix languages.

Context:
- Domain: {CONFIG['domain']}
- Service / Niche: {CONFIG['niche']}
- Target Region: {CONFIG['geo']}
- Target Audience: {CONFIG['audience']}
- Primary Keyword: {keyword}

Requirements:
- Length: 900-1100 words
- Structure: H1 title, 4-5 H2 sections, conclusion paragraph
- Tone: Professional, helpful, locally relevant
- Use the primary keyword naturally 3-5 times
- End with a subtle CTA: the domain is available for businesses in this niche
- Output ONLY the article in Markdown with this frontmatter:
---
title: "..."
date: {date_str}
description: "..."
keywords: ["{keyword}"]
---"""

def review_prompt(draft):
    return f"""You are an SEO editor. Review and improve this German article:
- Fix any unnatural or AI-sounding phrasing
- Ensure the primary keyword appears naturally 3-5 times
- Remove filler sentences
- Keep the same language, structure, and frontmatter
Return ONLY the improved article in Markdown. No commentary.

Article:
{draft}"""

# --- Validators ---
def validate_frontmatter(article):
    for field in ["title:", "date:", "description:", "keywords:"]:
        if field not in article:
            return False
    return True

def check_keyword_density(article, kw):
    count = article.lower().count(kw.lower())
    return 3 <= count <= 5

def is_duplicate(new_article):
    import glob
    for path in glob.glob("content/posts/*.md"):
        with open(path, encoding="utf-8") as f:
            old = f.read()
        if SequenceMatcher(None, old, new_article).ratio() > 0.7:
            return True
    return False

# --- Thumbnail ---
def fetch_thumbnail():
    try:
        r = requests.get(
            "https://api.unsplash.com/photos/random",
            params={"query": "lawyer legal Germany", "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {os.environ['UNSPLASH_KEY']}"}
        )
        img_url = r.json()["urls"]["regular"]
        img_data = requests.get(img_url, stream=True)
        os.makedirs("static/images", exist_ok=True)
        path = f"static/images/{date_str}-thumbnail.jpg"
        with open(path, "wb") as f:
            shutil.copyfileobj(img_data.raw, f)
        return f"/images/{date_str}-thumbnail.jpg"
    except Exception as e:
        print(f"Thumbnail failed: {e}")
        return ""

# --- Main ---
def main():
    print(f"Generating article for keyword: {keyword}")

    for attempt in range(3):
        try:
            # Generate
            draft = generate_with_fallback(generation_prompt())

            # Validate frontmatter
            if not validate_frontmatter(draft):
                print("Frontmatter missing, retrying...")
                continue

            # Check keyword density
            if not check_keyword_density(draft, keyword):
                print("Keyword density off, retrying...")
                continue

            # Check duplicate
            if is_duplicate(draft):
                print("Too similar to existing article, retrying...")
                continue

            # Review
            print("Reviewing article...")
            reviewed = generate_with_fallback(review_prompt(draft))

            # Fetch thumbnail
            thumbnail = fetch_thumbnail()

            # Add thumbnail to frontmatter
            if thumbnail:
                reviewed = reviewed.replace(
                    f'date: {date_str}',
                    f'date: {date_str}\nimage: "{thumbnail}"'
                )

            # Save
            os.makedirs("content/posts", exist_ok=True)
            filename = f"content/posts/{date_str}-{random.randint(1000,9999)}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(reviewed)

            print(f"Article saved: {filename}")

            with open(os.environ.get("GITHUB_ENV", "/dev/null"), "a") as f:
                f.write(f"ARTICLE_COUNT=1\n")

            return

        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)

    raise Exception("Failed after 3 attempts")

if __name__ == "__main__":
    main()
