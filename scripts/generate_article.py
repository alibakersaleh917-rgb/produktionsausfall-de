import requests, os, datetime, random, shutil, time
from difflib import SequenceMatcher

FLASH_KEYS = [os.environ["GEMINI_KEY_1"],os.environ["GEMINI_KEY_2"],os.environ["GEMINI_KEY_3"],os.environ["GEMINI_KEY_4"],os.environ["GEMINI_KEY_5"],os.environ["GEMINI_KEY_6"]]
CONFIG = {"domain":"anwaltsagent.de","niche":"Rechtsberatung / Legal Matching","geo":"Deutschland","audience":"Unternehmen und Privatpersonen","keywords":["Anwalt finden Deutschland","Rechtsanwalt beauftragen online","Anwaltssuche Deutschland","guenstige Rechtsberatung online","Anwalt Erstberatung Kosten","bester Anwalt Deutschland finden"]}
date_str = datetime.date.today().isoformat()
keyword = random.choice(CONFIG["keywords"])

def call_gemini(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={api_key}"
    r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=60)
    if r.status_code == 429:
        raise Exception("429")
    if r.status_code != 200:
        raise Exception(f"{r.status_code} {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def generate_with_fallback(prompt):
    for key in FLASH_KEYS:
        try:
            return call_gemini(prompt, key)
        except Exception as e:
            print(f"Key error: {str(e)[:100]}")
            if "429" in str(e):
                continue
            raise e
    raise Exception("All API keys exhausted")

def gen_prompt():
    return f"""Write a German SEO blog article for {CONFIG['domain']}. Write ONLY in German.\nPrimary Keyword: {keyword}\nLength: 900-1100 words. H1 + 4 H2 sections + conclusion.\nEnd with subtle CTA that domain is available.\nOutput ONLY Markdown with frontmatter:\n---\ntitle: \"...\"\ndate: {date_str}\ndescription: \"...\"\nkeywords: [\"{keyword}\"]\n---"""

def validate(article):
    return all(f in article for f in ["title:","date:","description:","keywords:"])

def main():
    print(f"Keyword: {keyword}")
    for attempt in range(3):
        try:
            draft = generate_with_fallback(gen_prompt())
            if not validate(draft):
                print("Frontmatter missing, retrying...")
                continue
            print("Reviewing...")
            reviewed = generate_with_fallback(f"Improve this German article SEO. Fix phrasing. Keep frontmatter. Return ONLY Markdown.\n\n{draft}")
            os.makedirs("content/posts", exist_ok=True)
            filename = f"content/posts/{date_str}-{random.randint(1000,9999)}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(reviewed)
            print(f"Saved: {filename}")
            return
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)
    raise Exception("Failed after 3 attempts")

if __name__ == "__main__":
    main()
