import requests, os, datetime, random, shutil, time
from difflib import SequenceMatcher
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]
MODEL = "meta-llama/llama-3.3-70b-instruct:free"
CONFIG = {"domain":"anwaltsagent.de","niche":"Rechtsberatung","geo":"Deutschland","audience":"Unternehmen und Privatpersonen","keywords":["Anwalt finden Deutschland","Rechtsanwalt beauftragen online","Anwaltssuche Deutschland","guenstige Rechtsberatung online","Anwalt Erstberatung Kosten","bester Anwalt Deutschland finden"]}
date_str = datetime.date.today().isoformat()
keyword = random.choice(CONFIG["keywords"])
def call_openrouter(prompt):
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":f"Bearer {OPENROUTER_KEY}","Content-Type":"application/json"},json={"model":MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":2000},timeout=120)
    if r.status_code != 200:
        raise Exception(f"{r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]
def gen_prompt():
    return f"Schreibe einen deutschen SEO-Artikel fuer {CONFIG['domain']}. NUR Deutsch.\nHaupt-Keyword: {keyword}\nLaenge: 1200-1500 Woerter. H1 + 5 H2 + Fazit.\nFrontmatter:\n---\ntitle: \"...\"\ndate: {date_str}\ndescription: \"...\"\nkeywords: [\"{keyword}\"]\n---"
def validate(a):
    return all(f in a for f in ["title:","date:","description:","keywords:"])
def main():
    print(f"Keyword: {keyword}")
    for attempt in range(3):
        try:
            draft = call_openrouter(gen_prompt())
            if not validate(draft):
                print("Frontmatter missing, retrying...")
                continue
            reviewed = call_openrouter(f"Verbessere diesen deutschen SEO-Artikel. Behalte Frontmatter. Nur Markdown.\n\n{draft}")
            if not validate(reviewed):
                reviewed = draft
            os.makedirs("content/posts",exist_ok=True)
            fname = f"content/posts/{date_str}-{random.randint(1000,9999)}.md"
            open(fname,"w",encoding="utf-8").write(reviewed)
            print(f"Saved: {fname}")
            return
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2**attempt)
    raise Exception("Failed after 3 attempts")
if __name__ == "__main__":
    main()
