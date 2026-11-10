# Ultimate B62: Discord Rich Presence screenshot reference

**Date 2026-11-10. Parent:** B61 Draft PR #126. **Source:** user's two screenshot references in this chat, plus [Discord official rich presence guidance](https://github.com/discord/discord-api-docs/blob/main/developers/discord-social-sdk/development-guides/setting-rich-presence.mdx).

## What the screenshots show

The actual French Discord user-profile screenshot shows the BBSC activity with app title, `In Cathedral Ward`, `BL 44 | Solo`, then an elapsed timer. The montage above it shows the app name, locations/encounters, BL/build and participation data, and **additional Russian captions**: `Одиночная игра`, `Сражение с боссом`, `Наблюдение после смерти`. A screenshot cannot prove whether these captions are additional *native* Rich Presence fields, user custom-status text, or text added in montage editing.

Discord's currently published Activity schema exposes only the user-controlled `details` and `state` text lines underneath the game/application name, plus `timestamps`, `party.size`, images, tooltips, supported platforms, join secrets, and a `status_display_type` that changes the **member list** label, not a third activity-card line. Image small/large text are tooltips, not independently positioned third lines. We do **not** inject newlines or promise impossible arbitrary layout.

## B62 actual implemented native Rich Presence format (ReferenceCard)

Normal session, opt-in BL/build enabled:
```text
BBSC: Yharnam Together  [Discord-registered application name, still pending registration]
In Central Yharnam      [details]
BL 25   STR Build · Co-op (2/5) [state]
15:55                   [session elapsed, example]
```

During boss:
```text
BBSC: Yharnam Together
Fighting Father Gascoigne
BL 25   STR Build · Co-op (2/5)
03:23                   [boss elapsed, example]
```

This **matches the two real customizable rows of the user-profile example**, not the three independent text rows the user originally requested in their conceptual mockup. The exact second-line font, horizontal alignment, dot separator and time are controlled by the Discord client. BL and Build are next to each other with exactly three ASCII spaces in our transmitted state (not justified opposite edges). Long state strings are trimmed to at most 120 bytes without slicing a UTF-8 continuation byte.

Spectating:
```text
Spectating in Central Yharnam
BL 25   STR Build · Co-op (2/5)
```
Boss name remains verified only by B60's read-only active gauge adapter. If unknown, `Boss fight`. For PvP duel or invader modes the boss detail never overrides authoritative PvP status. Privacy opt-outs remove local BL/build/area/boss independently.

## Architecture and user choice

- `bbport/gpu/bbcoop/discord_presence_policy.h`: new `PresenceLayout::ReferenceCard` mode alongside existing `PresenceLayout::StatusFirst` from B61 (do not delete the previous user-requested formatting). The new mode uses *details* for location or combat/spectate, *state* for adjacent BL/build plus membership/role, and *timestamps* for session or encounter time. StatusFirst retains details=`Central Yharnam | BL 25   STR Build` and state=`In co-op (2/5)` or `Fighting Father Gascoigne (2/5)`.
- `bbport/gpu/bbcoop/discord_status.cpp`: the **real Discord IPC publisher** selects ReferenceCard by default, or StatusFirst when `BB_DISCORD_REFERENCE_LAYOUT=0`. No additional Discord process, no game memory reads on the IPC worker.
- `bbport/launcher/bbport_coop.py`: saved `discord_reference_layout='1'` by default and clean launch-only `BB_DISCORD_REFERENCE_LAYOUT` environment propagation; off if RPC not enabled. Existing stat/build default privacy OFF until opt-in.
- `bbport/launcher/bbport_launcher_win.py`: a distinct local toggle `Discord card: location first` on the Co-op page. This selects between the screenshot-like layout and the earlier B61 two-row fallback.
- C++ tests in `bbport/tests/test_discord_activity.cpp`: exact screenshot-like scene, boss 2/5, timer switching, unknown name, spectate, invader/duel priority, privacy, and original B61 format. Python launcher tests check settings/clean environment. Win/Linux and GCC/Clang contracts in dedicated B62 workflow.

**Not guaranteed:** real Discord may collapse multiple ASCII spaces; native party size renders `(2 of 5)` when enabled by B61's optional `BB_DISCORD_NATIVE_PARTY_SIZE=1`, replacing the custom `(2/5)` suffix. Invites and actual rendering must be checked in a logged-in Discord test account with a legitimate registered app ID. We do not claim three independently configurable native text fields or a completed game playtest.

**No production access:** no Fornex change, save modification or proprietary asset duplication. Source-only Draft, require real Windows BBPort + 2–5 player rig QA.
