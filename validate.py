"""Validate country-check-data.json before it can be merged. Run: python validate.py"""
import json, sys, re

ERR = []
WARN = []
def err(m): ERR.append(m)

d = json.load(open("country-check-data.json", encoding="utf-8"))
m = d.get("meta", {})
if m.get("schema_version") != 1: err("meta.schema_version must be 1")
if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", m.get("updated", "")): err("meta.updated must be YYYY-MM-DD")
C, L, F, T = d.get("countries", {}), d.get("fto_listings", {}), d.get("fatf_evaluations", {}), d.get("crt_links", {})
if len(C) < 200: err(f"countries: {len(C)} entries, expected at least 200")
if len(L) < 50: err(f"fto_listings: {len(L)} entries, expected at least 50")

URL = re.compile(r"^https://[^\s\"]+$")
for k, o in C.items():
    if not o.get("n"): err(f"{k}: missing display name n")
    if o.get("fatf") not in (None, "black", "grey"): err(f"{k}: fatf must be black or grey")
    if o.get("fto", "a") not in ("y", "n", "a"): err(f"{k}: fto must be y, n or a")
    if o.get("fto") == "y" and not o.get("ftog"): err(f"{k}: fto is y but ftog is empty")
    for g in o.get("ftog", []):
        if g not in L: err(f"{k}: group '{g}' not in fto_listings")
    if o.get("us") not in (None, "c", "t"): err(f"{k}: us must be c or t")
    if o.get("us") and not o.get("usp"): err(f"{k}: us set but usp empty")
    for j in ("usp", "uk", "ca", "ch", "au", "eu", "un"):
        for e in o.get(j, []) or []:
            if not (isinstance(e, list) and len(e) == 2 and e[0] and URL.match(e[1])): err(f"{k}: bad {j} entry {e}")
    for e in o.get("eu", []) or []:
        if isinstance(e, list) and len(e) == 2 and not e[1].startswith("https://www.sanctionsmap.eu/#/main/details/"): err(f"{k}: eu link must be an EU Sanctions Map regime page: {e}")
    for e in o.get("un", []) or []:
        if isinstance(e, list) and len(e) == 2 and not e[1].startswith(("https://main.un.org/securitycouncil/", "https://digitallibrary.un.org/")): err(f"{k}: un link must be a UN page: {e}")
    if "cpi" in o and not (isinstance(o["cpi"], int) and 0 <= o["cpi"] <= 100): err(f"{k}: cpi out of range")
# Since 27 Oct 2026 the FTO view is U.S.-only: fto_listings is the list of U.S.-designated groups, each with an empty list.
# Other governments' listings are not kept; any label here fails the check, so no task can add them back.
for g, b in L.items():
    if b != []: err(f"fto_listings {g}: must be an empty list (other governments' FTO listings are not kept)")
if "fto_listing_evidence" in d: err("fto_listing_evidence: no longer used; remove it")
for k, v in F.items():
    if k not in C: WARN.append(f"fatf_evaluations: {k} has an evaluation but no country entry (territory shown on the map only)")
    if not (isinstance(v, list) and len(v) == 3 and re.fullmatch(r"\d{4}-\d{2}", v[0])): err(f"fatf_evaluations {k}: bad entry {v}")
for k, v in T.items():
    if k not in C: err(f"crt_links: {k} not a country key")
    if not re.fullmatch(r"[a-z0-9-]+", v): err(f"crt_links {k}: bad slug {v}")
nb = sum(1 for o in C.values() if o.get("fatf") == "black"); ng = sum(1 for o in C.values() if o.get("fatf") == "grey")
cnt = m.get("counts", {})
if cnt.get("fatf_black") != nb or cnt.get("fatf_grey") != ng: err(f"meta.counts FATF ({cnt.get('fatf_black')}/{cnt.get('fatf_grey')}) do not match data ({nb}/{ng})")

# Comprehensive U.S. embargoes are locked (Andrzej, 29 Oct 2026). These are the only U.S. sanctions that by themselves
# make a grant to anyone in the country unlawful, so a wrong "not comprehensive" here is the most harmful error the page
# can make. No data change can remove or downgrade them, and no data change can add a new one: either needs an edit to
# the lists below, which is a system change Andrzej merges himself. When OFAC genuinely lifts or adds an embargo, edit
# these lists in the same pull request as the data change. The weekly Federal Register watch (checks/check_sources.py)
# is how such a change is noticed.
COMPREHENSIVE = {"Cuba", "Iran", "North Korea"}
REGION_NOTES = {"Ukraine": ("Crimea", "Donetsk", "Luhansk")}
for k in sorted(COMPREHENSIVE):
    if k not in C: err(f"locked: {k} is missing from countries")
    elif C[k].get("us") != "c": err(f"locked: {k} must show a comprehensive U.S. embargo (us = c); lifting it needs Andrzej's edit to COMPREHENSIVE in validate.py")
    elif not C[k].get("usp"): err(f"locked: {k} must keep its OFAC program link")
for k, o in C.items():
    if o.get("us") == "c" and k not in COMPREHENSIVE: err(f"locked: {k} shows a comprehensive U.S. embargo that is not in COMPREHENSIVE; adding one needs Andrzej's edit to validate.py")
for k, words in REGION_NOTES.items():
    note = (C.get(k) or {}).get("usn") or ""
    for w in words:
        if w not in note: err(f"locked: {k} usn must name {w} (comprehensive embargo on occupied regions); changing it needs Andrzej's edit to REGION_NOTES in validate.py")

# Every country needs ISO codes so automated checks can match it to official datasets
for k, o in C.items():
    if not o.get("iso2") and o.get("n") not in ("Ashmore and Cartier Is.",):
        WARN.append(f"{o.get('n')}: no iso2 code; EU Sanctions Map check cannot cover it")

# Page dates and as-of text (meta.page): format checks only; 'checked' may never be in the future
import datetime as _dt
pg = m.get("page", {})
for k in ("cpi", "fatf", "fto", "sanc"):
    a, l = (pg.get("asof") or {}).get(k), (pg.get("layers") or {}).get(k) or {}
    if not isinstance(a, str) or not a or len(a) > 200 or "<" in a: err(f"meta.page.asof.{k}: missing or invalid")
    c = l.get("checked", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", c): err(f"meta.page.layers.{k}.checked: not a YYYY-MM-DD date")
    elif c > _dt.date.today().isoformat(): err(f"meta.page.layers.{k}.checked: {c} is in the future")
    w = l.get("when")
    if not isinstance(w, str) or not w or len(w) > 120 or "<" in w: err(f"meta.page.layers.{k}.when: missing or invalid")

for w in WARN: print("note:", w)
if ERR:
    print("INVALID:\n- " + "\n- ".join(ERR)); sys.exit(1)
print(f"OK: {len(C)} countries, {len(L)} FTO groups, FATF {nb} black / {ng} grey")
