# Country Check update procedure

The one procedure for changing any data value on Country Check. Page wording and layout are outside it (they are edited in WordPress).

## Roles
- **Proposer**: the weekday daily data check (scheduled task "Country Check daily data check"). Finds changes and opens pull requests. Never merges.
- **Verifier**: a separate scheduled task ("Country Check independent verifier"). Runs after the proposer, starts fresh, and is told to look for reasons each change is wrong. It sees the proposed values and the source URLs, never the proposer's reasoning.
- **Code checks**: `validate.py` and `checks/check_sources.py`, run by GitHub on every pull request. No judgment, no AI.
- **Andrzej**: notified, not asked, except for held changes.

## Steps for every change
1. **Proposer** opens one pull request per source event (for example, one Federal Register notice). The description must contain, for each changed value: field and country or group, old value, new value, official source URL, the quoted passage that supports it (under 50 words), and the corrections-log line if the change corrects an error.
2. **Code checks** run. Any error blocks the merge. A new non-U.S. FTO label cannot pass without an evidence pattern that matches the official list.
3. **Verifier** re-derives each change from the official source on its own, then from a second source where one exists (table below). It records a verdict per change in a pull-request comment: confirmed (with its own quote), or doubt (with the reason).
4. **Outcome**
   - All changes confirmed and no strict rule triggered: verifier adds the label `verified`. Auto-merge publishes. The site picks it up within six hours.
   - Any doubt, any disagreement with the outside tie-breaker, or any strict-rule change the verifier cannot confirm from two sources: label `held`. Andrzej is notified with a two-line summary. Held pull requests wait; nothing is published.
5. **Weekly summary** (Monday): what was published, what is held, what the weekly source check found.
6. **Reverting**: reverting the merge commit on GitHub restores the previous file; the site follows within six hours, or at once with `?ppcc_refresh=1` when an administrator loads the page.

## Strict rules (removals and FTO country placement)
These cause the most harm if wrong, so they need two confirmations:
- Removing any sanction program, FTO label or FATF listing.
- Changing a country's FTO presence (Identified, None identified, Not covered) or its group list.
- Any change touching more than five countries at once.
The verifier must confirm from two different sources (table below). If only one source exists, the change is held.

## Sources and second sources
| Data | Primary source | Second source or code check |
|---|---|---|
| U.S. FTO list | Federal Register notices | OpenSanctions U.S. FTO dataset (tie-breaker); State Department FTO page |
| FTO presence by country | State Department Country Reports on Terrorism, country chapter | Same report, Chapter 5 group profile "Areas of operation"; designation notice. Same publisher, so a partial second source only |
| Other bodies' FTO labels | UK, Canada, Australia lists; UN and EU consolidated lists | Code check with stored evidence patterns |
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
