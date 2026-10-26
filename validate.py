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
BODIES = {"EU", "EU military wing", "UK", "UN", "Canada", "Australia"}
for k, o in C.items():
    if not o.get("n"): err(f"{k}: missing display name n")
    if o.get("fatf") not in (None, "black", "grey"): err(f"{k}: fatf must be black or grey")
    if o.get("fto", "a") not in ("y", "n", "a"): err(f"{k}: fto must be y, n or a")
    if o.get("fto") == "y" and not o.get("ftog"): err(f"{k}: fto is y but ftog is empty")
    for g in o.get("ftog", []):
        if g not in L: err(f"{k}: group '{g}' not in fto_listings")
    if o.get("us") not in (None, "c", "t"): err(f"{k}: us must be c or t")
    if o.get("us") and not o.get("usp"): err(f"{k}: us set but usp empty")
    for j in ("usp", "uk", "ca", "ch", "au"):
        for e in o.get(j, []) or []:
            if not (isinstance(e, list) and len(e) == 2 and e[0] and URL.match(e[1])): err(f"{k}: bad {j} entry {e}")
    for j in ("eu", "un"):
        if j in o and not all(isinstance(x, str) and x for x in o[j]): err(f"{k}: bad {j} list")
    if "cpi" in o and not (isinstance(o["cpi"], int) and 0 <= o["cpi"] <= 100): err(f"{k}: cpi out of range")
for g, b in L.items():
    bad = set(b) - BODIES
    if bad: err(f"fto_listings {g}: unknown bodies {bad}")
for k, v in F.items():
    if k not in C: WARN.append(f"fatf_evaluations: {k} has an evaluation but no country entry (territory shown on the map only)")
    if not (isinstance(v, list) and len(v) == 3 and re.fullmatch(r"\d{4}-\d{2}", v[0])): err(f"fatf_evaluations {k}: bad entry {v}")
for k, v in T.items():
    if k not in C: err(f"crt_links: {k} not a country key")
    if not re.fullmatch(r"[a-z0-9-]+", v): err(f"crt_links {k}: bad slug {v}")
nb = sum(1 for o in C.values() if o.get("fatf") == "black"); ng = sum(1 for o in C.values() if o.get("fatf") == "grey")
cnt = m.get("counts", {})
if cnt.get("fatf_black") != nb or cnt.get("fatf_grey") != ng: err(f"meta.counts FATF ({cnt.get('fatf_black')}/{cnt.get('fatf_grey')}) do not match data ({nb}/{ng})")

# Every non-U.S. label must carry an evidence pattern that the source check can test against the official list
EV = d.get("fto_listing_evidence", {})
for g, bodies in L.items():
    for b in bodies:
        if b in ("UK", "Canada", "Australia", "UN", "EU", "EU military wing") and not EV.get(g, {}).get(b):
            err(f"fto_listings {g}: label {b} has no evidence pattern in fto_listing_evidence")
        if EV.get(g, {}).get(b):
            try: re.compile(EV[g][b])
            except re.error as e: err(f"fto_listing_evidence {g}/{b}: bad pattern ({e})")
for g in EV:
    if g not in L: err(f"fto_listing_evidence: {g} is not in fto_listings")
# Every country needs ISO codes so automated checks can match it to official datasets
for k, o in C.items():
    if not o.get("iso2") and o.get("n") not in ("Ashmore and Cartier Is.",):
        WARN.append(f"{o.get('n')}: no iso2 code; EU Sanctions Map check cannot cover it")

for w in WARN: print("note:", w)
if ERR:
    print("INVALID:\n- " + "\n- ".join(ERR)); sys.exit(1)
print(f"OK: {len(C)} countries, {len(L)} FTO groups, FATF {nb} black / {ng} grey")
