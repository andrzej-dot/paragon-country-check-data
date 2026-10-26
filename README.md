# Country Check master data

The single source of truth for the data on Country Check (paragonphilanthropy.com/country-indicators/).

## How it works
1. `country-check-data.json` holds every data value the page shows: per-country corruption score, FATF status, FTO presence and groups, sanctions programs in seven jurisdictions with official links; the other bodies that list each FTO; latest FATF evaluations; State Department Country Reports on Terrorism links; and the as-of dates.
2. Changes are made only by pull request. The daily data check (the proposer) opens a pull request for each change with the official source URL, the quoted passage and a corrections-log line. A separate scheduled agent (the verifier) re-derives each change from the sources without seeing the proposer's reasoning and posts its verdicts with its own quotes. See `PROCEDURE.md`.
3. Three automatic checks must pass before a pull request can merge: `validate.py` (structure), `checks/check_sources.py` (every label and EU regime tested against the official lists; Federal Register, World Bank and OpenSanctions cross-checks; links; and `checks/check_evidence.py`, which confirms every proposer quote word for word in its source) and `verifier-signoff` (the verifier confirmed every change, with its own quotes, also checked word for word). Auto-merge then publishes. Anything labelled `held` waits for Andrzej, who is notified. The same source check also runs weekly on the published file and opens an issue if anything has drifted.
4. The WordPress site (snippet in `wordpress/ppcc-data-sync.php`, installed through Code Snippets) pulls the approved file from the main branch every six hours, validates it again, keeps the last good copy, and clears the page cache. Visitors' browsers never contact GitHub. No password or token is stored anywhere.
5. Page wording and layout are not in this repository; they stay in WordPress.

## Field reference
See the Country Check page specification in the Paragon Workspace: `Marketing/Website/Country Indicators/Country-Indicators-Page-Spec.md`.
