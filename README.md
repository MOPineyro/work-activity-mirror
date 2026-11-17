# Work activity mirror

This repository contains **synthetic, backdated placeholder commits** that mirror the daily contribution counts publicly displayed on my work profile, [@mop-moxfive](https://github.com/mop-moxfive). The original engineering work belongs to that account. Each marker represents one counted activity, including commits, pull requests, or reviews.

`activity.json` stores the imported daily totals. The initial import on November 16, 2026 began with 968 verified merged work commits; subsequent imports use the full public calendar. The mirror contains aggregate counts only. Work code, commit messages, repository names, and private email addresses are excluded. Markers use my GitHub-provided noreply address.

## Automatic updates

The [Sync work activity workflow](https://github.com/MOPineyro/work-activity-mirror/actions/workflows/sync-activity.yml) runs daily at **06:17 UTC (03:17 in Buenos Aires)**. GitHub may delay scheduled jobs. Run it anytime from **Actions → Sync work activity → Run workflow**.

The workflow reads the same public calendar shown on the work profile and appends only missing markers. It publishes in batches of at most 500 so large catch-up runs are indexed by GitHub. It needs no personal access token, custom secret, or access to work repositories. GitHub's built-in repository token publishes the markers. Private contribution visibility must stay enabled on the source account.

For a local preview, run `python3 scripts/sync_activity.py --dry-run`. To import and publish in batches, run `python3 scripts/sync_activity.py --push` from a clean checkout. Dates come directly from the source calendar; author and committer timestamps use noon UTC on each historical day.

Imported days remain in history as the source's rolling calendar advances. If GitHub reduces a previously imported day's count, the sync stops for review instead of rewriting published history. GitHub can disable schedules in public repositories after 60 days without repository activity; re-enable the workflow from Actions if that happens.

The personal profile includes these synthetic markers plus existing personal activity and setup commits, so its total can differ from the work profile. This is an activity mirror, not a transfer of original commits, PRs, or reviews.
