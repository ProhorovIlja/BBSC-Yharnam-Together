# Ultimate B61: corrected Discord row ordering and compact BL / Build spacing

**2026-11-10. Based on B60 Draft #125.** User corrected the Rich Presence target (twice) and specifically clarified that `BL 25` and `STR Build` must be **adjacent**, with a small gap, **not opposite edges of a row and not separated by vertical pipe characters**. This source change corrects that exact misunderstanding.

## User's requested visual hierarchy (desired custom HUD or mockup)

```text
BBSC: Yharnam Together
Central Yharnam
BL 25   STR Build
In co-op (2/5)
15:55
```

In a boss fight, the first two information rows remain unchanged, while the third and fourth informational rows become:

```text
BBSC: Yharnam Together
Central Yharnam
BL 25   STR Build
Fighting Father Gascoigne (2/5)
03:23
```

The three spaces mean **compact adjacent information**, not left and right margins. These are **visual design targets**, not live Discord screenshots.

## Actual Discord platform limitation and truthful RPC fallback

The standard [Discord Rich Presence activity](https://github.com/discord/discord-api-docs/blob/main/developers/discord-social-sdk/development-guides/setting-rich-presence.mdx) supports: one registered app name; **two independently supplied lines**, `details` and `state`; native party-size metadata; and an elapsed timestamp. It **cannot** create a third independent info line, force left/right columns, or programmatically insert a distinct level/build row between details and state. Avoid misleading claims or fake newline formatting.

Actual **source-level** payload now therefore has:
- name (app registration): `BBSC: Yharnam Together` (NOT registered at this writing; B57 supports operator-supplied valid ID).
- details: `Central Yharnam | BL 25   STR Build`, with location and validated opted-in level/build grouped in that single native line. When only one stat field is displayed, the `| ` separator before it remains.
- state normal: `In co-op (2/5)`; state during boss: `Fighting Father Gascoigne (2/5)`, with unknown bosses `Boss fight (2/5)`. Spectators: `Spectating` (never mislabel the spectating hunter as actively Fighting). Invading, duels, downed and dead retain B56 precedence.
- timer normal: overall session timestamp. Timer during a boss fight (only when boss privacy is ON): B60's actual game-thread encounter start timestamp, reverting to session after combat.
- native Discord `party.size` automatically appends `(2 of 5)`. Therefore **B61 defaults to explicit `(2/5)` without native size**, to match user request. Optional `BB_DISCORD_NATIVE_PARTY_SIZE=1` re-enables native Discord party counter; then state omits the manual suffix, avoiding duplication. Actual Discord desktop join-button/party-size tradeoff must be verified before publishing; do not claim it is preserved in all clients.

## Code edited

- `bbport/gpu/bbcoop/discord_presence_policy.h`: keep details fixed during boss and change the state field only. `BL 25` and `STR Build` append as `BL 25   STR Build`, **three spaces, no `|` between the two**, no layout justification. Boss/time privacy and B60 name checks remain.
- `bbport/gpu/bbcoop/discord_status.cpp`: explicitly manage native party-size vs manual compact count without double suffixes.
- `bbport/tests/test_discord_activity.cpp`: assert precise source string (including three-space gap), stable details during boss, state `Fighting Father Gascoigne (2/5)`, timers and role precedence, privacy and 16 existing STR/SKL/BLT/ARC >=18 classifier masks.
- Inherited B58/B59 CI assertions updated to current user-approved formatting and kept as regressions. B61 adds own Windows/Linux source contracts and GCC/Clang C++20 policy regression.

## Still required

Real Discord desktop screenshot using a properly registered Ultimate Application ID, all supported CUSA 1.09 in-game validation, local level/build update tests, real boss gauge verification for DLC/Chalice, no stale boss state after wipes/loads, and end-to-end 2–5-hunter co-op. Discord may normalize or trim multiple ASCII spaces and truncate long strings, so exact visual spacing must be checked in the actual desktop client; no promise to force its renderer.

No Fornex production, game saves, asset redistribution or live deployment. Remains Draft only.
