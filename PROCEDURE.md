# Country Check update procedure

The one procedure for changing any data value on Country Check. Page wording and layout are outside it (they are edited in WordPress).

## Roles
- **Proposer**: the weekday daily data check (scheduled task "Country Check daily data check"). Finds changes and opens pull requests. Never merges.
- **Verifier**: a separate scheduled Claude task ("Country Check independent verifier") with its own context. It sees the proposed values and source URLs, never the proposer's reasoning, and is told to look for reasons each change is wrong. Andrzej decided on 26 Oct not to add a model from another company; the word-for-word quote check is the main protection against a shared misreading or an invented quote.
- **Code checks**: `validate.py`, `checks/check_sources.py` and `checks/check_evidence.py`, run by GitHub on every pull request. No judgment, no AI. `check_evidence.py` fetches each cited page itself (or its Internet Archive copy if the site refuses servers) and fails unless every quote appears in it word for word.
- **Andrzej**: notified, not asked, except for held changes.

## Steps for every change
1. **Proposer** opens one pull request per source event (for example, one Federal Register notice). The description must contain, for each changed value: field and country or group, old value, new value, official source URL, the quoted passage that supports it (under 50 words), and the corrections-log line if the change corrects an error. The same entries go in a file `evidence/YYYY-MM-DD-<topic>.json` as a list of {"path", "new", "url", "quote"} so code can check them.
2. **Code checks** run. Any error blocks the merge.
3. **Verifier** re-derives each change from the official source on its own, then from a second source where one exists (table below). It posts one comment beginning `<!-- country-check-verifier -->` with a ```json block listing, per changed value, {"path", "verdict": "confirmed" or "doubt", "url", "quote", "reason"}, then adds the label `verifier-done`. Code then checks every verifier quote word for word.
4. **Outcome**
   - All verdicts confirmed and every quote found: the sign-off check passes and auto-merge publishes. The site picks it up within six hours.
   - Any doubt, a quote not found, or a strict change without two source URLs: the check fails and nothing is published. The verifier adds `held` and Andrzej is notified with a two-line summary.
5. **Weekly summary** (Monday): what was published, what is held, what the weekly source check found.
6. **Reverting**: reverting the merge commit on GitHub restores the previous file; the site follows within six hours, or at once with `?ppcc_refresh=1` when an administrator loads the page.

## Page dates ("as of" and "last checked")
The page's as-of lines and each view's "checked" date come from `meta.page` in the data file. A view shows "being updated" once its checked date is older than its maximum age (corruption 400 days, FATF 150, FTO 35, sanctions 35).
- The proposer moves a view's `checked` date forward only after it has, in that same run, confirmed that view against its sources and found nothing to change (FTO: Federal Register and State Department FTO list; sanctions: every jurisdiction's regime list; FATF: the latest plenary outcome; corruption: World Bank release). If any source could not be reached, the date stays put.
- Date-only changes touch `meta`, which the evidence check does not cover, so they publish once the structure check passes. The structure check rejects future dates and malformed text.
- When a view is within seven days of going stale and cannot be confirmed, the proposer notifies Andrzej.

## Changes to the system itself
Any pull request that touches anything other than `country-check-data.json` and `evidence/` (checks, workflows, this procedure, the website snippet) fails the sign-off check by design and never publishes automatically. Andrzej merges those himself, so no agent can weaken the controls on its own.

## Standing decisions (Andrzej; every task follows these, and none may reverse them)
If a task prompt, an older note or a source seems to call for something below, these decisions win. Do not act on the conflict: say so in your notification and leave it for Andrzej.

1. **FTOs are U.S. only** (27 Oct 2026, confirmed 29 Oct). The FTO view shows only Foreign Terrorist Organizations designated by the U.S. State Department (INA section 219). `fto_listings` is the list of those groups, each with an empty list. Never add another government's or body's listing (EU, UK, UN, Canada, Australia or any other); `validate.py` rejects any. Adding a newly designated group or removing a revoked one is normal data work.
2. **FTO country presence comes only from the latest Country Reports on Terrorism** (29 Oct 2026). Do not fill presence from older editions. A group the report lists only by region gets no country presence.
3. **Every U.S.-designated FTO must be in the file.** The source check errors if OpenSanctions lists a U.S. FTO the file lacks (29 Oct 2026).
4. **Sanctions cover seven jurisdictions, each entry with its official link** (29 Oct 2026). Order on the page: UN, EU, United States, UK, Canada, Switzerland, Australia. Every entry is [name, official URL]: UN entries link to the Security Council committee page (the resolution 1701 arms embargo, which has no committee, links to the resolution in the UN Digital Library); EU entries link to that regime's EU Sanctions Map page, and the source check confirms the id matches the regime.
5. **Only the U.S. row says Comprehensive or Targeted** (29 Oct 2026). That is OFAC's own classification. The other six jurisdictions show "In force" or "None"; never characterize their sanctions as comprehensive or targeted.
6. **Sanctions wording is jurisdiction-neutral** (27 Oct 2026): "country-specific sanctions", not U.S. terms such as "country program".
7. **No automatic approval for scheduled runs** (29 Oct 2026). Some sites (for example dfat.gov.au) cannot be opened in a scheduled run without approval. When a view nears its stale date because a source could not be checked, notify Andrzej; he runs one attended check.
8. **Tasks never edit the website or WordPress.** Page wording and layout change only in sessions with Andrzej.
9. **Comprehensive U.S. embargoes are locked** (29 Oct 2026). Cuba, Iran and North Korea must show a comprehensive U.S. embargo, and Ukraine's note must name Crimea, Donetsk and Luhansk; no other country may show one. `validate.py` enforces this. Lifting, adding or changing one needs an edit to the lists in `validate.py`, a system change Andrzej merges himself. The weekly Federal Register sanctions watch opens an issue listing new OFAC and presidential sanctions items so such changes are noticed.
9. **Never weaken a check to get a change through.** If a check blocks a change you believe is right, hold it and notify Andrzej; changes to checks, procedure or prompts go through a pull request that he merges.

## Strict rules (removals and FTO country placement)
These cause the most harm if wrong, so they need two confirmations:
- Removing any sanction program or FATF listing.
- Changing a country's FTO presence (Identified, None identified, Not covered) or its group list.
- Any change touching more than five countries at once.
The verifier must confirm from two different sources (table below). If only one source exists, the change is held.

## Sources and second sources
| Data | Primary source | Second source or code check |
|---|---|---|
| U.S. FTO list | Federal Register notices | OpenSanctions U.S. FTO dataset (tie-breaker); State Department FTO page |
| FTO presence by country | State Department Country Reports on Terrorism, country chapter | Same report, Chapter 5 group profile "Areas of operation"; designation notice. Same publisher, so a partial second source only |
| U.S. sanctions | OFAC sanctions program pages | Comprehensive embargoes locked in `validate.py`; weekly Federal Register sanctions watch (issue); link check |
| EU sanctions | EU Sanctions Map API | Code check, plus the EU consolidated list |
| UK, Canada, Switzerland, Australia sanctions | Each government's regime page | Link check, plus OpenSanctions where it covers the regime |
| UN sanctions | UN Security Council consolidated list | Code check of regime list types |
| FATF | FATF plenary public statements | FATF high-risk and monitored jurisdictions pages |
| Corruption score | Transparency International CPI | World Bank Control of Corruption (direction-of-change sanity check only) |

## Rebuilds (to catch errors both agents share)
- **Monthly sample**: the rebuild task picks 10 countries and 5 FTO groups at random and rebuilds every value from the official sources without looking at the current file. Differences become a `held` pull request.
- **Annual full rebuild**: every value rebuilt from scratch each February, after the CPI release. Differences are reviewed the same way.
- **Weekly source check**: GitHub runs `checks/check_sources.py` on the published file every Monday and opens an issue if anything has drifted.

## Honest limits
- Both agents are the same kind of model, so they can share a misreading. The code checks, the outside tie-breaker and the rebuilds reduce this. They do not remove it.
- Where only prose is available (FTO presence by country), there is no code check. The strict rules and holds are the protection.
- Both agents act through the same GitHub connection, so independence is procedural (separate tasks, separate instructions, no shared reasoning), not a separate identity.
