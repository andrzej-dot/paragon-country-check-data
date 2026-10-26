"""Mechanical evidence check for a data pull request. No judgment, no AI.

Usage (from the repository root, inside a pull request checkout):
  python checks/check_evidence.py proposer BASE_REF            # proposer's evidence files
  python checks/check_evidence.py verifier BASE_REF COMMENTS   # verifier's comment (COMMENTS = JSON file of PR comments)

What it enforces
1. Every changed data value (countries.<key>.<field>, fto_listings.<group>, fatf_evaluations.<key>, crt_links.<key>)
   is covered by an evidence entry whose "new" equals the value now in the file.
2. Every quoted passage actually appears, word for word, in the official page it cites (fetched here, fresh;
   if the site refuses servers, the latest Internet Archive copy is used).
3. Strict changes (any removal, any FTO presence or group change, or more than five countries) need two
   different source URLs.
4. Verifier mode: the verifier's comment (marker <!-- country-check-verifier -->) must mark every changed value
   "confirmed" with its own quote, which is checked the same way. Any "doubt" fails the check.
Evidence entry: {"path": "countries.AFG.eu", "new": <value>, "url": "https://...", "quote": "..."}
Proposer evidence lives in evidence/*.json files added by the pull request.
"""
import json, re, sys, html, subprocess, urllib.request, unicodedata

UA = {"User-Agent": "Mozilla/5.0 (Paragon Country Check evidence check)"}
MARK = "<!-- country-check-verifier -->"
EXEMPT = ("meta", "fto_listing_evidence")

def load_base(ref):
    return json.loads(subprocess.check_output(["git", "show", f"{ref}:country-check-data.json"]))

def changed_paths(old, new):
    out = {}
    def put(p, o, n): out[p] = (o, n)
    for sec in ("fto_listings", "fatf_evaluations", "crt_links"):
        a, b = old.get(sec, {}), new.get(sec, {})
        for k in set(a) | set(b):
            if a.get(k) != b.get(k): put(f"{sec}.{k}", a.get(k), b.get(k))
    a, b = old.get("countries", {}), new.get("countries", {})
    for k in set(a) | set(b):
        oa, ob = a.get(k) or {}, b.get(k) or {}
        for f in set(oa) | set(ob):
            if f in ("iso2", "iso3"): continue
            if oa.get(f) != ob.get(f): put(f"countries.{k}.{f}", oa.get(f), ob.get(f))
    return out

def is_removal(o, n):
    if o in (None, "", [], {}): return False
    if n in (None, "", [], {}): return True
    if isinstance(o, list) and isinstance(n, list): return any(x not in n for x in o)
    return False

def norm(t):
    t = unicodedata.normalize("NFKC", t)
    t = t.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "}))
    return re.sub(r"\s+", " ", t).strip().lower()

_cache = {}
def page_text(url):
    if url in _cache: return _cache[url]
    txt, src = None, None
    for u, label in ((url, "live"), ("https://web.archive.org/web/2id_/" + url, "archive")):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
                raw = r.read().decode("utf-8", "ignore")
            raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
            txt, src = norm(html.unescape(re.sub(r"<[^>]+>", " ", raw))), label
            break
        except Exception:
            continue
    if txt is None and not url.startswith("https://web.archive.org/"):
        # The site refuses servers and no archive copy exists yet: ask the Internet Archive to capture it, then read that copy.
        try:
            urllib.request.urlopen(urllib.request.Request("https://web.archive.org/save/" + url, headers=UA), timeout=120).read()
            with urllib.request.urlopen(urllib.request.Request("https://web.archive.org/web/2id_/" + url, headers=UA), timeout=60) as r:
                raw = r.read().decode("utf-8", "ignore")
            raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
            txt, src = norm(html.unescape(re.sub(r"<[^>]+>", " ", raw))), "archive (captured now)"
        except Exception:
            pass
    _cache[url] = (txt, src)
    return txt, src

def check_entries(entries, changes, who, errors, need_verdict=False):
    by_path = {}
    for e in entries:
        p = e.get("path")
        if p not in changes:
            errors.append(f"{who}: evidence for {p}, which this pull request does not change"); continue
        if need_verdict and e.get("verdict") != "confirmed":
            errors.append(f"{who}: {p} marked '{e.get('verdict')}': {e.get('reason', '')}"); continue
        if not need_verdict and e.get("new") != changes[p][1]:
            errors.append(f"{who}: {p} evidence says new value {e.get('new')!r} but the file has {changes[p][1]!r}"); continue
        q, u = norm(e.get("quote") or ""), e.get("url") or ""
        if len(q) < 15 or not u.startswith("https://"):
            errors.append(f"{who}: {p} needs an https source URL and a quote of at least 15 characters"); continue
        txt, src = page_text(u)
        if txt is None:
            errors.append(f"{who}: {p} source could not be fetched (live or archive): {u}"); continue
        if q not in txt:
            errors.append(f"{who}: {p} quote not found word for word in {u} ({src} copy): \"{e.get('quote')}\""); continue
        by_path.setdefault(p, set()).add(u)
    strict_countries = {p.split(".")[1] for p in changes if p.startswith("countries.")}
    for p, (o, n) in changes.items():
        urls = by_path.get(p, set())
        if not urls:
            errors.append(f"{who}: no valid evidence for {p}"); continue
        strict = is_removal(o, n) or p.startswith("fto_listings.") or p.endswith((".fto", ".ftog")) or len(strict_countries) > 5
        if strict and len(urls) < 2:
            errors.append(f"{who}: {p} is a strict change (removal, FTO presence or more than five countries) and needs two different source URLs")

def main():
    mode, base = sys.argv[1], sys.argv[2]
    new = json.load(open("country-check-data.json", encoding="utf-8"))
    changes = changed_paths(load_base(base), new)
    if not changes:
        print("No data values changed; nothing to evidence."); return 0
    errors = []
    if mode == "proposer":
        files = subprocess.check_output(["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD", "--", "evidence/"]).decode().split()
        entries = []
        for f in files:
            try: entries += json.load(open(f, encoding="utf-8"))
            except Exception as e: errors.append(f"proposer: {f} is not valid JSON ({e})")
        if not files: errors.append("proposer: no evidence/*.json file added by this pull request")
        check_entries(entries, changes, "proposer", errors)
    else:
        comments = json.load(open(sys.argv[3], encoding="utf-8"))
        vc = [c for c in comments if MARK in (c.get("body") or "")]
        if not vc:
            errors.append("verifier: no verifier comment yet")
        else:
            body = vc[-1]["body"]
            m = re.search(r"```json\s*(\[.*?\])\s*```", body, re.S)
            if not m: errors.append("verifier: comment has no ```json [...]``` block")
            else: check_entries(json.loads(m.group(1)), changes, "verifier", errors, need_verdict=True)
    print(f"Changed values ({len(changes)}):")
    for p, (o, n) in sorted(changes.items()): print(f" - {p}: {o!r} -> {n!r}")
    if errors:
        print("\nFAILED:"); [print(" -", e) for e in errors]; return 1
    print("\nOK: every change is backed by a quote found word for word in its official source.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
