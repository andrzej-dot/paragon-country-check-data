"""Deterministic checks of country-check-data.json against structured official sources.
Run from the repository root: python checks/check_sources.py [--since YYYY-MM-DD]
Prints a report and writes checks/report.json. Exit code 0 = no errors, 1 = errors found.
No judgment calls are made here; anything that needs reading prose is left to the verifier agent."""
import json, re, sys, html, urllib.request, xml.etree.ElementTree as ET, datetime as dt

UA = {"User-Agent": "Mozilla/5.0 (Paragon Country Check data check)"}
def get(url, timeout=90):
    print("fetch", url[:80], file=sys.stderr)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

D = json.load(open("country-check-data.json", encoding="utf-8"))
C, L = D["countries"], D["fto_listings"]
since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else D["meta"]["updated"]
R = {"errors": [], "warnings": [], "info": [], "unreachable": []}
def E_(m): R["errors"].append(m)
def W(m): R["warnings"].append(m)
def I(m): R["info"].append(m)

def textlist(url, tags):
    s = get(url).decode("utf-8", "ignore")
    out = []
    for t in tags:
        out += [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<%s[^>]*>(.*?)</%s>" % (t, t), s, re.S)]
    return out

# Other governments' FTO lists (UK, Canada, Australia, UN, EU) are not checked: the FTO view is U.S.-only since 27 Oct 2026.
Q = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})

# 3. U.S. FTO designations and revocations in the Federal Register since the last update
try:
    q = "https://www.federalregister.gov/api/v1/documents.json?per_page=100&conditions%5Bterm%5D=%22Foreign+Terrorist+Organization%22&conditions%5Bagencies%5D%5B%5D=state-department&conditions%5Bpublication_date%5D%5Bgte%5D=" + since
    docs = json.loads(get(q)).get("results", [])
    for x in docs:
        W(f"Federal Register {x.get('publication_date')}: {x.get('title')} ({x.get('html_url')}). Verifier to decide whether LISTED/RISK change.")
    pi = json.loads(get("https://www.federalregister.gov/api/v1/public-inspection-documents/current.json")).get("results", [])
    for x in pi:
        if "Foreign Terrorist Organization" in (x.get("title") or "") or "Terrorist" in (x.get("title") or ""):
            W(f"Federal Register public inspection (not yet published): {x.get('title')} ({x.get('html_url')})")
except Exception as e: R["unreachable"].append(f"Federal Register: {e}")

# 3b. U.S. sanctions watch: new OFAC rules and notices, and presidential sanctions orders, in the Federal Register.
# Nothing here is an error (OFAC publishes routinely, and an error would block every data change). Each item goes to
# R["watch"]; the weekly run opens an issue listing them so Andrzej sees anything that might add, lift or change a
# country program, above all the locked comprehensive embargoes in validate.py.
R["watch"] = []
try:
    wsince = (dt.date.today() - dt.timedelta(days=8)).isoformat() if "--weekly" in sys.argv else since
    base = "https://www.federalregister.gov/api/v1/documents.json?per_page=100&order=newest&fields%5B%5D=title&fields%5B%5D=html_url&fields%5B%5D=publication_date&fields%5B%5D=type&conditions%5Bpublication_date%5D%5Bgte%5D=" + wsince
    seen = set()
    for q in (base + "&conditions%5Bagencies%5D%5B%5D=foreign-assets-control-office",
              base + "&conditions%5Btype%5D%5B%5D=PRESDOCU&conditions%5Bterm%5D=sanctions+OR+%22blocking+property%22+OR+%22national+emergency%22"):
        for x in json.loads(get(q)).get("results", []):
            if x.get("html_url") in seen: continue
            seen.add(x.get("html_url"))
            t = x.get("title") or ""
            hot = [k for k in ("Cuba", "Cuban", "Iran", "North Korea", "Korea", "Ukraine", "Crimea", "Venezuela", "Syria", "Russia", "Belarus") if k.lower() in t.lower()]
            R["watch"].append(f"{x.get('publication_date')} {x.get('type')}: {t} ({x.get('html_url')})" + (f"  [names: {', '.join(hot)}]" if hot else ""))
    I(f"Sanctions watch since {wsince}: {len(R['watch'])} Federal Register item(s)")
except Exception as e: R["unreachable"].append(f"Federal Register sanctions watch: {e}")

# 4. EU country regimes (EU Sanctions Map) against the eu field
try:
    rg = json.loads(get("https://www.sanctionsmap.eu/api/v1/regime"))["data"]
    by2 = {o.get("iso2"): k for k, o in C.items() if o.get("iso2")}
    want, ids = {}, {}
    for r in rg:
        code = ((r.get("country") or {}).get("data") or {}).get("code")
        spec = (r.get("specification") or "").strip()
        if not code or code not in by2 or "satisfying of certain claims" in spec or code == "US": continue
        want.setdefault(by2[code], set()).add(spec.rstrip("."))
        ids.setdefault((by2[code], spec.rstrip(".")), set()).add(r.get("id"))
    for k, specs in want.items():
        have = {x[0].rstrip(".") for x in (C[k].get("eu") or [])}
        for name, url in (C[k].get("eu") or []):
            m = re.search(r"/details/(\d+)/", url)
            if not m or int(m.group(1)) not in ids.get((k, name.rstrip(".")), set()):
                E_(f"EU {C[k]['n']}: link for '{name}' does not point to that regime on the EU Sanctions Map ({url})")
        for s in specs - have: E_(f"EU {C[k]['n']}: regime on the EU Sanctions Map missing from page: {s}")
        for s in have - specs: E_(f"EU {C[k]['n']}: page shows a regime not on the EU Sanctions Map: {s}")
    for k, o in C.items():
        if o.get("eu") and k not in want: E_(f"EU {o['n']}: page shows EU measures but the EU Sanctions Map has none for this country")
except Exception as e: R["unreachable"].append(f"EU Sanctions Map: {e}")

# 5. World Bank Control of Corruption scores, only when the source has been updated
try:
    src = json.loads(get("https://api.worldbank.org/v2/sources?format=json&per_page=200"))[1]
    wgi = next((s for s in src if s.get("id") == "3"), None)
    I(f"World Bank WGI last updated {wgi.get('lastupdated') if wgi else 'unknown'}")
    if wgi and wgi.get("lastupdated", "") > "2026-09-25":
        W("World Bank WGI has been updated since 2026-09-25: run the score refresh.")
except Exception as e: R["unreachable"].append(f"World Bank: {e}")

# 6. Every official link resolves
urls = set()
for o in C.values():
    for j in ("usp", "uk", "ca", "ch", "au", "eu", "un"):
        for e in o.get(j) or []: urls.add(e[1])
for slug in set(D.get("crt_links", {}).values()):
    urls.add(f"https://www.state.gov/reports/country-reports-on-terrorism-2024/{slug}/")
from concurrent.futures import ThreadPoolExecutor
import time
def chk1(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=15) as r:
            return r.status, None
    except urllib.error.HTTPError as e: return e.code, None
    except Exception as e: return None, type(e).__name__
def chk(u):
    code, err = chk1(u)
    if err or code >= 400:          # retry once after a pause: government sites often refuse bursts from servers
        time.sleep(8); code, err = chk1(u)
    return u, code, err
# state.gov answers some automated requests with 404 even when the page exists (seen 26 Oct 2026 from GitHub's servers),
# so a 404 there is a warning for the verifier to confirm in a browser, not an error.
SOFT404 = ("www.state.gov",)
if "--no-links" not in sys.argv:
    with ThreadPoolExecutor(6) as ex:
        for u, code, err in ex.map(chk, sorted(urls)):
            if err: R["unreachable"].append(f"Link {u}: {err}")
            elif code in (404, 410) and any(h in u for h in SOFT404): W(f"Link {u}: HTTP {code} from the server; verifier to open it in a browser to confirm whether it was removed")
            elif code in (404, 410): E_(f"Link {u}: HTTP {code} (page removed)")
            elif code >= 400: R["unreachable"].append(f"Link {u}: HTTP {code}")
    print("links checked", file=sys.stderr)

# 7. Outside tie-breaker: OpenSanctions (independent aggregator). Never an automatic change: a group in the file but not in OpenSanctions is a warning; a group in OpenSanctions but not in the file is an error.
try:
    import gzip
    os_url = "https://data.opensanctions.org/datasets/latest/us_state_terrorist_orgs/targets.simple.csv"
    import csv, io
    rows = list(csv.DictReader(io.StringIO(get(os_url).decode("utf-8", "ignore"))))
    names = [(r.get("name", "") + ";" + r.get("aliases", "")).translate(Q) for r in rows]
    I(f"OpenSanctions U.S. FTO dataset: {len(rows)} entries")
    for g in L:
        base = re.sub(r"\s*\([^)]*\)$", "", g)
        abbr = re.search(r"\(([^)]+)\)$", g)
        if not any(re.search(re.escape(base), n, re.I) or (abbr and re.search(r"\b%s\b" % re.escape(abbr.group(1)), n)) for n in names):
            W(f"OpenSanctions: {g} not matched by name in the U.S. FTO dataset. Verifier to confirm it is still designated.")
    # Reverse direction: every group OpenSanctions lists as a U.S. FTO must be in the file. A group missing from
    # the file is an error (it blocks merges and the weekly check opens an issue) so an omission cannot go unnoticed.
    def _n(s): return re.sub(r"[^a-z0-9]+", " ", s.translate(Q).lower()).strip()
    keys = []
    for g in L:
        keys.append(_n(re.sub(r"\s*\([^)]*\)$", "", g)))
        keys += [_n(x) for x in re.findall(r"\(([^)]+)\)", g)]
        keys.append(_n(g))
    keys = [k for k in keys if k]
    for r in rows:
        cands = [_n(x) for x in [r.get("name", "")] + (r.get("aliases", "") or "").split(";") if x.strip()]
        if not any(c == k or (len(k) >= 6 and k in c) or (len(c) >= 6 and c in k) for c in cands for k in keys):
            E_(f"OpenSanctions lists '{r.get('name')}' as a U.S. FTO but the file has no matching group. Check the State Department FTO list and add it, or record why not.")
    if len(rows) != len(L):
        W(f"OpenSanctions has {len(rows)} U.S. FTO entries; page has {len(L)} groups. Verifier to reconcile.")
except Exception as e: R["unreachable"].append(f"OpenSanctions: {e}")

json.dump(R, open("checks/report.json", "w"), indent=1)
for k in ("errors", "warnings", "watch", "unreachable", "info"):
    print(f"\n{k.upper()} ({len(R[k])})")
    for m in R[k]: print(" -", m)
sys.exit(1 if R["errors"] else 0)
