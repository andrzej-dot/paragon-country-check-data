"""Confirms the public page is serving the approved data file (added 24 Nov 2026, audit SE-94).

The website copies country-check-data.json from this repository every six hours. If that copy stops (a failed fetch,
a cache that will not clear, a snippet switched off), the page keeps showing older data and nothing else would notice.
This script reads the live page as a visitor's browser receives it and compares the data embedded in it with the file
on main. Run daily by the "Validate data" workflow:
  python checks/check_live.py
Exit code 1 when the page's data differs from main and main's last change is more than 12 hours old (time enough for
two sync cycles), or when the page carries no data at all.
"""
import datetime as dt, json, re, subprocess, sys, urllib.request, random

PAGE = "https://paragonphilanthropy.com/country-indicators/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
PARTS = ("countries", "fto_listings", "fatf_evaluations", "crt_links")

def embedded(html):
    m = re.search(r"window\.PPCC_DATA\s*=\s*", html)
    if not m: return None
    i, depth, ins, esc = m.end(), 0, False, False
    for j in range(i, len(html)):
        c = html[j]
        if ins:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return json.loads(html[i:j + 1])
    return None

def main():
    want = json.load(open("country-check-data.json", encoding="utf-8"))
    html = urllib.request.urlopen(urllib.request.Request(f"{PAGE}?v={random.randint(1, 10**9)}", headers={"User-Agent": UA}), timeout=60).read().decode("utf-8", "ignore")
    got = embedded(html)
    if got is None:
        print("ERROR: the live page carries no Country Check data (window.PPCC_DATA missing); visitors see only the built-in fallback."); return 1
    diffs = [p for p in PARTS if got.get(p) != want.get(p)]
    if (got.get("meta") or {}).get("page") != (want.get("meta") or {}).get("page"): diffs.append("meta.page (dates and as-of text)")
    if not diffs:
        print("OK: the live page serves the data on main."); return 0
    last = subprocess.run(["git", "log", "-1", "--format=%cI", "--", "country-check-data.json"], capture_output=True, text=True).stdout.strip()
    age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last)).total_seconds() / 3600 if last else 99
    msg = f"live page differs from main in: {', '.join(diffs)} (main's data last changed {age:.1f} hours ago)"
    if age <= 12:
        print("OK (sync pending): " + msg); return 0
    print("ERROR: " + msg + ". The website's copy has stopped updating; check the Country Check data sync snippet (ppcc_last_error) and the page cache."); return 1

if __name__ == "__main__":
    sys.exit(main())
