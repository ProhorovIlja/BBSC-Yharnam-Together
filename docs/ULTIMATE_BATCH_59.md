# Ultimate B59: Discord `Build` suffix, boss action and compact co-op count

**2026-11-10. Parent:** [B58 Draft #123](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/123). **User request:** `STR Build` / `STR/ARC Build` rather than bare abbreviated names, location and `BL 25`, `In co-op (2/5)`, elapsed session timer; while fighting, `Fighting <Boss Name>` and the **boss-fight** timer.

## Actual Discord Rich Presence capabilities and the chosen presentation

Per the [official Discord Rich Presence guide](https://github.com/discord/discord-api-docs/blob/main/developers/discord-social-sdk/development-guides/setting-rich-presence.mdx), there is an automatic app name, **two controlled text rows** (`details` and `state`), an optional native party counter and a distinct elapsed timer. Discord does **not** expose three independent custom text rows. Preserve every field but pack the level and class next to the location in `details`, with the network role in `state`:

```text
BBSC: Yharnam Together                   [Discord application name; registration required]
In Central Yharnam | BL 25 | STR Build   [details]
In co-op (2 of 5)                       [state + native party.size]
10:35 elapsed                            [Discord timestamp, sample only]
```

If no native party counter is available but the local size is known, format `In co-op (2/5)` directly. **Never** send a manual `(2/5)` and native `party.size` together, or invent member counts to enable invites. A real Discord app ID configured through B57 launcher is still mandatory. The SDK/Discord itself controls exact ordering, line-breaks, elapsed wording and visual availability.

```text
BBSC: Yharnam Together
Fighting Cleric Beast | Central Yharnam | BL 25 | STR/ARC Build
In co-op (2 of 5)
02:41 elapsed                            [current boss-fight time, sample only]
```

A player already spectating a boss instead displays `Watching Cleric Beast` in `details` and `Spectating` in `state` so dead observers are not falsely labeled as combatants. If the boss is unknown, `Boss fight`; never fabricate a boss identity. On boss exit, timestamp resets to the original session start (existing B56 implementation). If the player hides the boss, the boss-only timer is hidden, but permitted area/BL/build remain.

## Implemented source changes

- `bbport/gpu/bbcoop/discord_presence_policy.h`: adds the text ` Build` at presentation time, not into B45's `DiscordShort` classifier. This preserves 16 concise stat masks at >=18 and leaves existing in-game HUD/full English/Russian names unchanged. Uses `Fighting` for known active boss fights, `Watching` when spectating, `Boss fight` without a verified name, and the shorter user-selected `In co-op` state with `N/M` fallback.
- `bbport/gpu/bbcoop/discord_status.cpp`: updates Discord asset **hover** title to `BBSC: Yharnam Together`. The visible application name is controlled by Discord's registered application ID, not the asset hover text; no registration or app ID is fabricated.
- `bbport/tests/test_discord_activity.cpp`: asserts the actual new text, solo and co-op roles, B59 privacy, spectating and fight-vs-session elapsed timestamps, along with existing B45/58 all-16-builds and native party counter regressions. The test uses a *supplied* `Cleric Beast` fixture; the production game still does not identify the specific boss by name.
- Inherited B56/B57/B58 CI source contracts are aligned with the new user wording; independent B59 CI runs Windows/Linux text contracts and GCC/Clang C++20 policy tests.

## Remaining release gates and dependencies

1. Register and package a **genuine Ultimate Discord Application ID**; provide game artwork under that application. A tooltip is **not** a registered name. Confirm actual desktop render.
2. Validate the game-thread encounter identity for all supported CUSA 1.09 variations, DLC and Chalice dungeons before connecting exact names; current runtime only knows `boss_fighting`, not `Cleric Beast`. The timer starts when Discord polls the observed encounter, currently around every two seconds, not at a guaranteed exact engine combat event.
3. Verify B56/57 level and offensive-stat snapshots update when a character levels up or switches slots and that protected locations/names cannot leak when the corresponding privacy switch is off.
4. Actual Windows BBPort client/launcher build and 2–5 player tests, long localized names, runtime Discord IPC reliability, no duplicates, preserve existing invites. **Separate** invasion DBNO/HUD networking is still pending; this batch does not claim to implement it.
5. No Fornex production edits, no game save changes and no proprietary game/mod assets incorporated.

**Status:** source-level formatting fix with regression coverage, not a released playable feature.
