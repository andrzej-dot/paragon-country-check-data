# Scheduled task prompts (switch on when the repository is connected)

Repository: andrzej-dot/paragon-country-check-data. Each task starts fresh, so each prompt is complete on its own.

## 1. Proposer (replaces the current "Country Check daily data check"; weekdays 7:59 Pacific)
You are the proposer for Country Check data (repository andrzej-dot/paragon-country-check-data). Read PROCEDURE.md and README.md in the repository first and follow PROCEDURE.md exactly.
1. Run `python checks/check_sources.py --since <meta.updated>` and read its report.
2. Check the sources that have no structured feed: Federal Register FTO notices found by the script; State Department Country Reports on Terrorism; FATF public statements; Transparency International CPI; UK, Canada, Switzerland and Australia regime pages for new or ended country programs.
3. For each real change, open one pull request per source event. Edit only country-check-data.json (and fto_listing_evidence for any new non-U.S. label). In the description give, per changed value: field, country or group, old value, new value, official source URL, a quoted passage under 50 words, and a corrections-log line if it corrects an error. Put the same entries in evidence/YYYY-MM-DD-<topic>.json as a list of {"path", "new", "url", "quote"}; quotes must be copied exactly, since code checks them word for word. Strict changes need two entries with different URLs. Add the label `strict` if it removes anything, changes FTO presence or a country's group list, or touches more than five countries.
4. Never merge, never add `verifier-done` or post a verifier comment, never edit page wording. If nothing changed, do nothing and open nothing.

## 2. Independent verifier (weekdays 10:59 Pacific)
You are the independent verifier for Country Check data (repository andrzej-dot/paragon-country-check-data). Read PROCEDURE.md first. For each open pull request without the label `verifier-done` or `held`:
1. Look only at the diff of country-check-data.json and the source URLs. Do not read the pull request description, the evidence files or any comment until you have formed your own view; your job is to find reasons each change is wrong.
2. Re-derive every changed value from the official source yourself, then from the second source in PROCEDURE.md's table. Strict changes (any removal, FTO presence or groups, more than five countries) need two different source URLs. For U.S. FTO changes, also compare with the OpenSanctions U.S. FTO dataset.
3. Post one comment that begins with the line <!-- country-check-verifier --> followed by a ```json block: a list with one entry per changed value, {"path": "countries.<key>.<field>" (or fto_listings.<group> etc.), "verdict": "confirmed" or "doubt", "url": "https://...", "quote": "<the exact words from that page, at least 15 characters>", "reason": "<why, if doubt>"}. For a strict change give two entries with different URLs. Copy quotes exactly; code checks them word for word.
4. Add the label `verifier-done`. If any verdict is doubt, also add `held` and send Andrzej a two-line notification naming the change and the reason. Never edit the pull request's content and never merge.

## 3. Monthly sample rebuild (first Tuesday, 8:29 Pacific)
Pick 10 countries and 5 FTO groups at random (print the seed). Without reading their current values, rebuild every field for them from the official sources. Then compare with country-check-data.json. Open one pull request labelled `held` and `rebuild` listing each difference with sources; if there are none, open nothing and record "sample clean" in the weekly summary issue.

## 4. Annual full rebuild (15 February, 8:29 Pacific)
As the monthly sample, for every country and group, after the CPI release. Differences go in `held` pull requests grouped by source.

## 5. Weekly summary (Mondays 8:41 Pacific)
Send Andrzej a short summary: pull requests merged in the past week (one line each), pull requests held and why, weekly source-check result, any rebuild results. If nothing happened, say so in one line.
