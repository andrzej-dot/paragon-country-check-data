# Scheduled task prompts (switch on when the repository is connected)

Repository: andrzej-dot/paragon-country-check-data. Each task starts fresh, so each prompt is complete on its own.

## 1. Proposer (replaces the current "Country Check daily data check"; weekdays 7:59 Pacific)
You are the proposer for Country Check data (repository andrzej-dot/paragon-country-check-data). Read PROCEDURE.md and README.md in the repository first and follow PROCEDURE.md exactly.
1. Run `python checks/check_sources.py --since <meta.updated>` and read its report.
2. Check the sources that have no structured feed: Federal Register FTO notices found by the script; State Department Country Reports on Terrorism; FATF public statements; Transparency International CPI; UK, Canada, Switzerland and Australia regime pages for new or ended country programs.
3. For each real change, open one pull request per source event. Edit only country-check-data.json (and fto_listing_evidence for any new non-U.S. label). In the description give, per changed value: field, country or group, old value, new value, official source URL, a quoted passage under 50 words, and a corrections-log line if it corrects an error. Add the label `strict` if it removes anything, changes FTO presence or a country's group list, or touches more than five countries.
4. Never merge, never add `verified`, never edit page wording. If nothing changed, do nothing and open nothing.

## 2. Independent verifier
Not a scheduled Claude task. It is a GitHub Actions workflow (.github/workflows/verify.yml) that runs on every data pull request and calls a different company's model (decision D9), with the instructions in verifier/INSTRUCTIONS.md. It applies `verified` or `held`. Set up in Step 4.

## 3. Monthly sample rebuild (first Tuesday, 8:29 Pacific)
Pick 10 countries and 5 FTO groups at random (print the seed). Without reading their current values, rebuild every field for them from the official sources. Then compare with country-check-data.json. Open one pull request labelled `held` and `rebuild` listing each difference with sources; if there are none, open nothing and record "sample clean" in the weekly summary issue.

## 4. Annual full rebuild (15 February, 8:29 Pacific)
As the monthly sample, for every country and group, after the CPI release. Differences go in `held` pull requests grouped by source.

## 5. Weekly summary (Mondays 8:41 Pacific)
Send Andrzej a short summary: pull requests merged in the past week (one line each), pull requests held and why, weekly source-check result, any rebuild results. If nothing happened, say so in one line.
