"""Read log: the record behind every "checked" date on the page (added 24 Nov 2026, audit SE-94).

Before this, a date pull request could move a view's "checked" date forward with nothing to show which sources were
actually read. Now a view's date may move only if evidence/reads/<date>.json records that, on that date, every
required source for that view was read successfully. validate.py enforces this for every checked date from
2026-11-25 on, so a date can no longer be advanced on a task's say-so.

Usage (from the repository root):
  python checks/read_log.py cpi fatf fto sanc
      Reads every required source for the named views (plain request, then a real browser) and writes
      evidence/reads/<today>.json. Prints which views may have their date moved today.
  python checks/read_log.py --add URL --via "Fetch sources run 123456" --sha256 HEX --bytes N
      Records a source read another way (for example through the "Fetch sources" workflow artifact) in today's log.
"""
import datetime as dt, hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Every source that must be read before a view's date may move. A source counts as read when a log entry's url
# starts with the prefix below and ok is true. Changing this list is a system change (Andrzej's merge).
REQUIRED = {
    "cpi": ["https://api.worldbank.org/v2/sources"],
    "fatf": ["https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html"],
    "fto": [
        "https://www.federalregister.gov/api/v1/documents.json",
        "https://www.federalregister.gov/api/v1/public-inspection-documents/current.json",
        "https://www.state.gov/foreign-terrorist-organizations",
    ],
    "sanc": [
        "https://ofac.treasury.gov/sanctions-programs-and-country-information",
        "https://www.sanctionsmap.eu/api/v1/regime",
        "https://main.un.org/securitycouncil/",
        "https://www.gov.uk/government/collections/uk-sanctions-regimes-under-the-sanctions-act",
        "https://www.international.gc.ca/world-monde/international_relations-relations_internationales/sanctions/",
        "https://www.seco.admin.ch/",
        "https://www.legislation.gov.au/",
    ],
}
# The exact URL read_log.py opens for each required prefix.
FETCH = {
    "https://api.worldbank.org/v2/sources": "https://api.worldbank.org/v2/sources?format=json&per_page=200",
    "https://www.federalregister.gov/api/v1/documents.json": "https://www.federalregister.gov/api/v1/documents.json?per_page=20&conditions%5Bterm%5D=%22Foreign+Terrorist+Organization%22&conditions%5Bagencies%5D%5B%5D=state-department&order=newest",
    "https://main.un.org/securitycouncil/": "https://main.un.org/securitycouncil/en/sanctions/information",
    "https://www.international.gc.ca/world-monde/international_relations-relations_internationales/sanctions/": "https://www.international.gc.ca/world-monde/international_relations-relations_internationales/sanctions/current-actuelles.aspx?lang=eng",
    "https://www.seco.admin.ch/": "https://www.seco.admin.ch/de/sanktionsverordnungen",
    "https://www.legislation.gov.au/": "https://www.legislation.gov.au/F2011L02673/latest/versions",
}
MIN_BYTES = 2000  # an error page or an empty shell is not a read


def log_path(day):
    return os.path.join("evidence", "reads", f"{day}.json")


def load(day):
    p = log_path(day)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def covered(entries, view):
    """Required prefixes for a view that the entries do not show as read."""
    ok = [e.get("url", "") for e in entries if e.get("ok") and int(e.get("bytes") or 0) >= MIN_BYTES and e.get("sha256")]
    return [p for p in REQUIRED[view] if not any(u.startswith(p) for u in ok)]


def save(day, entries):
    os.makedirs(os.path.dirname(log_path(day)), exist_ok=True)
    json.dump(entries, open(log_path(day), "w", encoding="utf-8"), indent=1)


def main():
    day = dt.date.today().isoformat()
    entries = load(day)
    if "--add" in sys.argv:
        a = sys.argv
        url, via = a[a.index("--add") + 1], a[a.index("--via") + 1]
        sha, n = a[a.index("--sha256") + 1], int(a[a.index("--bytes") + 1])
        entries.append({"url": url, "ok": n >= MIN_BYTES, "bytes": n, "sha256": sha, "via": via,
                        "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
        save(day, entries); print(f"recorded {url} ({n} bytes) via {via}"); return 0
    from fetch import page_text
    views = [v for v in sys.argv[1:] if v in REQUIRED] or list(REQUIRED)
    for v in views:
        for p in REQUIRED[v]:
            url = FETCH.get(p, p)
            txt, how = page_text(url, raw=True)
            b = (txt or "").encode("utf-8")
            entries.append({"url": url, "ok": bool(txt) and len(b) >= MIN_BYTES, "bytes": len(b),
                            "sha256": hashlib.sha256(b).hexdigest() if txt else "", "via": how or "FAILED",
                            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            print(f"{v}: {'ok' if entries[-1]['ok'] else 'NOT READ'} {url}")
    save(day, entries)
    for v in views:
        miss = covered(entries, v)
        print(f"{v}: date may move today" if not miss else f"{v}: date must NOT move; unread: {', '.join(miss)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
