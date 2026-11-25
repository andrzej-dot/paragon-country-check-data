"""Checks that every FTO presence pair on the page still rests on its recorded basis (added 24 Nov 2026, audit SE-94).

evidence/basis/fto-presence.json holds one row per country and group pair shown as FTO presence: the official source
and the passage it rests on. validate.py makes sure every pair has a row. This script opens every source and confirms
each quoted passage is still there, word for word (spacing and line breaks ignored, since most quotes come from the
report PDF). Run weekly by the "Validate data" workflow and by the monthly sample rebuild:
  python checks/check_basis.py
Exit code 1 if any quote is not found or any source cannot be read.
"""
import json, os, re, subprocess, sys, tempfile, unicodedata, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import UA, page_text
from check_evidence import is_official

def squash(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = t.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "­": ""}))
    return re.sub(r"\s+", "", t)

_pdf = {}
def pdf_text(url):
    if url not in _pdf:
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120).read()
            with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
                f.write(raw); f.flush()
                _pdf[url] = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True, timeout=300).stdout
        except Exception as e:
            print(f"cannot read {url}: {e}", file=sys.stderr); _pdf[url] = None
    return _pdf[url]

def main():
    rows = json.load(open("evidence/basis/fto-presence.json", encoding="utf-8"))
    errors, texts = [], {}
    for r in rows:
        u, who = r["url"], f"{r['country']} / {r['group']}"
        if not is_official(u): errors.append(f"{who}: source is not an official site: {u}"); continue
        if u not in texts:
            texts[u] = squash(pdf_text(u) if u.lower().endswith(".pdf") else page_text(u, raw=True)[0])
        if not texts[u]: errors.append(f"{who}: source could not be read: {u}"); continue
        if squash(r["quote"]) not in texts[u]: errors.append(f"{who}: quote no longer found in {u}: \"{r['quote'][:120]}\"")
    print(f"FTO presence basis: {len(rows)} pairs, {len(texts)} sources, {len(errors)} problem(s)")
    for e in errors: print(" -", e)
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
