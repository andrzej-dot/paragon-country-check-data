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
C, L, EV = D["countries"], D["fto_listings"], D.get("fto_listing_evidence", {})
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

LISTS = {}
# Only counter-terrorism regimes count for "possible missing label" warnings (a group listed under, say, the Haiti regime is not a terrorist listing).
TERROR_UN = {"Al-Qaida"}
TERROR_EU = {"TERR", "EUAQ", "TAQA", "HAM"}
TERROR_NAMES = {}
Q = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})
SRC = {
 "UK": ("https://www.gov.uk/government/publications/proscribed-terror-groups-or-organisations--2/proscribed-terrorist-groups-or-organisations-accessible-version", ["h3"]),
 "Canada": ("https://www.publicsafety.gc.ca/cnt/ntnl-scrt/cntr-trrrsm/lstd-ntts/crrnt-lstd-ntts-en.aspx", ["h2", "h3"]),
 "Australia": ("https://www.nationalsecurity.gov.au/what-australia-is-doing/terrorist-organisations/listed-terrorist-organisations", ["td", "p", "a", "li", "strong"]),
}
for k, (u, tags) in SRC.items():
    try: LISTS[k] = textlist(u, tags)
    except Exception as e: R["unreachable"].append(f"{k} list: {e}")
try:
    t = ET.fromstring(get("https://scsanctions.un.org/resources/xml/en/consolidated.xml"))
    un_names, un_types = [], set()
    for e in t.iter("ENTITY"):
        lt = e.findtext("UN_LIST_TYPE"); un_types.add(lt)
        nm = [e.findtext("FIRST_NAME") or ""] + [a.findtext("ALIAS_NAME") or "" for a in e.iter("ENTITY_ALIAS")]
        un_names += nm
        if lt in TERROR_UN: TERROR_NAMES.setdefault("UN", []).extend(nm)
    LISTS["UN"] = [n for n in un_names if n]
    I("UN list types present: " + ", ".join(sorted(x for x in un_types if x)))
except Exception as e: R["unreachable"].append(f"UN list: {e}")
try:
    eu_names = []
    for ev, el in ET.iterparse(urllib.request.urlopen(urllib.request.Request("https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw", headers=UA), timeout=180)):
        if el.tag.split("}")[-1] == "sanctionEntity":
            nm = [c.get("wholeName") for c in el if c.tag.split("}")[-1] == "nameAlias" and c.get("wholeName")]
            eu_names += nm
            progs = {c.get("programme") for c in el if c.tag.split("}")[-1] == "regulation"}
            if progs & TERROR_EU: TERROR_NAMES.setdefault("EU", []).extend(nm)
            el.clear()
    LISTS["EU"] = eu_names; LISTS["EU military wing"] = eu_names
except Exception as e: R["unreachable"].append(f"EU list: {e}")

# 1. Every listing label must still be supported by its evidence pattern on the official list
for g, bodies in L.items():
    for b in bodies:
        if b not in LISTS: continue
        pat = EV.get(g, {}).get(b)
        if not pat: E_(f"Label {g} / {b}: no evidence pattern recorded"); continue
        if not any(re.search(pat, x, re.I) for x in LISTS[b]):
            E_(f"Label {g} / {b}: not found on the {b} list any more (pattern '{pat}'). Possible delisting or renaming.")
# 2. Possible missing labels: the group's own name found on a list where it carries no label
for g, bodies in L.items():
    base = re.sub(r"\s*\([^)]*\)$", "", g)
    if len(base) < 6: continue
    for b in ("UK", "Canada", "Australia", "UN", "EU"):
        if b in bodies or b not in LISTS or (b == "EU" and "EU military wing" in bodies): continue
        pool = TERROR_NAMES.get(b, []) if b in ("UN", "EU") else LISTS[b]
        if any(re.search(r"\b%s\b(?![-\u2013])" % re.escape(base), x.translate(Q), re.I) for x in pool):
            W(f"Label {g}: name appears on the {b} list but no {b} label is shown. Verifier to confirm whether it is the same group.")

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

# 4. EU country regimes (EU Sanctions Map) against the eu field
try:
    rg = json.loads(get("https://www.sanctionsmap.eu/api/v1/regime"))["data"]
    by2 = {o.get("iso2"): k for k, o in C.items() if o.get("iso2")}
    want = {}
    for r in rg:
        code = ((r.get("country") or {}).get("data") or {}).get("code")
        spec = (r.get("specification") or "").strip()
        if not code or code not in by2 or "satisfying of certain claims" in spec or code == "US": continue
        want.setdefault(by2[code], set()).add(spec.rstrip("."))
    for k, specs in want.items():
        have = {x.rstrip(".") for x in (C[k].get("eu") or [])}
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
    for j in ("usp", "uk", "ca", "ch", "au"):
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
for k in ("errors", "warnings", "unreachable", "info"):
    print(f"\n{k.upper()} ({len(R[k])})")
    for m in R[k]: print(" -", m)
sys.exit(1 if R["errors"] else 0)
