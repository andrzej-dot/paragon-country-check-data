"""Read an official web page as plain text, the same way every time.

Some official sites (fatf-gafi.org, and state.gov on some days) refuse plain server requests but serve a real
browser. So: try a plain request first; if refused, open the page in a headless Chromium browser. There is no
third-party fallback (no Internet Archive copy): official sources only (Andrzej, 2 Nov 2026). If both fail, the page
is unreadable and the change is held.

Used by check_evidence.py (word-for-word quote check), check_sources.py and the "Fetch sources" workflow.
Command line: python checks/fetch.py URL [URL ...]   prints, per URL, how it was read and the page text.
"""
import html, re, sys, urllib.request, unicodedata

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def norm(t):
    t = unicodedata.normalize("NFKC", t)
    t = t.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "}))
    return re.sub(r"\s+", " ", t).strip().lower()


def _strip(raw):
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    return html.unescape(re.sub(r"<[^>]+>", " ", raw))


def _plain(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
        return _strip(r.read().decode("utf-8", "ignore"))


_browser = None


def _browser_text(url, tries=3):
    """Open the page in headless Chromium. Returns the visible text, or None."""
    global _browser
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    if _browser is None:
        pw = sync_playwright().start()
        b = pw.chromium.launch(args=["--disable-http2"])
        _browser = b.new_context(user_agent=UA, locale="en-US")
    for _ in range(tries):
        page = _browser.new_page()
        try:
            r = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            if r is not None and r.status < 400:
                return page.inner_text("body")
        except Exception:
            pass
        finally:
            page.close()
    return None


_cache = {}


def page_text(url, raw=False):
    """Returns (text, how) where how is 'live' or 'live (browser)'; (None, None) if unreadable.
    text is normalised (lower case, single spaces) unless raw=True."""
    key = (url, raw)
    if key in _cache:
        return _cache[key]
    txt, how = None, None
    try:
        txt, how = _plain(url), "live"
    except Exception:
        t = _browser_text(url)
        if t:
            txt, how = t, "live (browser)"
    out = (txt if raw or txt is None else norm(txt), how)
    _cache[key] = out
    return out


if __name__ == "__main__":
    for u in sys.argv[1:]:
        t, how = page_text(u, raw=True)
        print(f"===== {u}\n===== read: {how or 'FAILED'}\n")
        print(t or "")
        print()
