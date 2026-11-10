# Ultimate B46: cross-chat canonical intake, real browser dedup and native Windows build gate

2026-11-10. Stacked on [B45 Draft PR #104](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/104). This is a cumulative validation checkpoint, NOT a released playable game.

## Actual work

- Created [cross-chat requirement master](ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md) documenting exact two mission interpretation, all previously recorded gameplay/server/launcher/website/network/PVP/voice/build/map/cheat/privacy issues and their Issue/PR acceptance status; historical archive sources and evidence boundaries retained.
- Created [cross-chat archive manifest](ULTIMATE_CROSS_CHAT_SOURCE_MANIFEST.md) from a current authorized Google Drive query of `Bloodborne — Seamless Hunt — HANDOFF / 01-HISTORY-MD` on the authorized private Drive account: **28 actual history items**, with private links retained only in the authorized Drive handoff. Four larger 2026-11-03/04/05/07/08/09 history contents were selectively inspected using bounded queries, and the private Nov 9 bug intake + original two missions charter were read. An indexed historical file is not a claim to have replayed every earlier ChatGPT turn. No private game files, keys, screenshots or account data were copied to GitHub.
- Actual in-game player browser bug: `lobby.members` and the bounded `lobby.players` can contain the same authenticated hunter; previous B43 `DrawPlayersPage` appended both arrays and displayed duplicates, inflating visible counts and creating repeated invite actions. Replaced the double raw push with `BbRoster::AppendUniqueOnline`, comparing canonical nonempty online account IDs, preferring the team row (real verified level/status), skipping offline members and preserving two different accounts with the same character name. Empty IDs are not treated as identity evidence, and no invite button is offered for an unknown/empty recipient ID.
- Portable C++20 fixture `test_roster_dedup.cpp`: overlapping account in team + shard, same display name on different IDs, offline entries, multiple unknown identity rows, 100 repeated snapshots, team row level wins. CI source test asserts actual ImGui code uses the tested helper, not an unused disconnected test function.
- New automatic CI includes prior B45 Windows/Linux social preference checks, B46 manifest/roster source checks, native standalone C++20 regression under GCC/Clang, and an **actual MSYS2 CLANG64 Windows production bbport build** using six source-only dependencies and the repo's `bbport/build.sh`, checking PE/AMD64 executable headers. This is deliberate *cumulative* native build coverage after B43-B46 UI work rather than needless full rebuild after each tiny commit; never upload binaries or game files. If compiler CI fails, diagnose the bounded first errors and keep Draft.

## New public upstream watch candidate, no blind transplant

- Original independent droogie [BBHost #233](https://github.com/droogie/bbhost/pull/233) now merged at checkpoint: CPU/draw-ahead path improvements for Windows <=60 fps, 6GB graphics cards and less than 16 threads, plus Windows UTF-8 non-ASCII file paths. **57 files changed** in its own runtime; not directly ABI-compatible with bbport/shadPS4/YT. Needs scoped microbenchmark and compatibility study before source adaptation.
- Original independent droogie [BBHost #217](https://github.com/droogie/bbhost/pull/217): unmerged real signaling handshake, connection lifecycle and spectator camera. Author explicitly warns client+server must update in lockstep. Do NOT graft one side onto YT/shadNet and break online.
- [BBHost #231](https://github.com/droogie/bbhost/pull/231) in review: controller glyph generation based on game files and device. Existing YT Input glyph settings may cover some use cases; compare behavior before duplication.
- Official YT upstream branch candidates include `invasions`, `invasions-game`, `rig/teams-apart-invasions`, `amelia-night`, `boss-hp-after-wipe`, `chalice-door`, `chalice-entry-fix`, `chalice-join` and NPC branches. Branch name is **discovery, not proof of a missing fix**. Analyze actual diffs with the Ultimate fork before reuse.
- Source panorama remains [2026-11-09 repo discovery of 241 candidates](ULTIMATE_GLOBAL_SOURCE_INTAKE_20261109.md). No search can certify scanning every GitHub repository, branch or unindexed previous chat.

## Release / trust boundary

- Current main working state remains stacked Draft B42 #98 -> B43 #101 -> B44 #102 -> B45 #104 -> B46, plus parallel #91/#92 and other earlier integration work not magically merged. A Draft with source CI cannot be described as user-installable.
- User-supplied old chat archives, screenshot descriptions, voice/DM needs, per-save progress and NPC issues remain tracked as unresolved until actual in-game reproduction and fix. Parent Fornex production, live accounts and player saves untouched.
- Build/test success is not guaranteed until the Actions run concludes. A successful Windows native **compile** still is not proof a real Bloodborne 1.09 game launches, displays the UI or plays correctly across 2–5 hunters.

## Follow-ups

1. Reconcile parallel #91/#92 with the stacked B46 branch only after conflict and protocol review.
2. Fix the next confirmed client compile or real-world guest/host regression from CI, not arbitrary speculative game offsets.
3. Continue measured upstream BBHost vs BBPort comparison plus P0 NPC/progression/world-state issues; include new user-reported bugs in the central ledger and correct Drive folder.
