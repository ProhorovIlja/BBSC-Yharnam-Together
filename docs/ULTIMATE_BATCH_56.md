# Ultimate B56: richer Discord status and faction-safe invasion policy

**10 November 2026.** Source: user request, tracked at [Issue #119](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/119), stacked on B55 Draft #118.

## What was already working (do not reimplement)
- `bbport/gpu/bbcoop/discord_status.cpp`: real local Discord IPC with location, play-session time, team size and join invites; basic duel/downed state. It is enabled only by the launcher's `BB_DISCORD_STATUS` and app ID; no Discord account token or SDK needed.
- `bbport/gpu/shim/bbport_overlay.cpp` team settings: leader-only `Invaders` toggle sends `TeamRequest.INVADERS`; global server `Invasions=false` overrides it.
- `emulator/src/core/bloodborne_invasion.h` / `docs/INVASIONS.md`: **one invader only**, no DBNO; death immediately ends invasion. Vitals of hostile members are excluded from defender party panel, but this is **not** an independent invader-squad HUD.

## Actual B56 source change
- New `bbport/gpu/bbcoop/discord_presence_policy.h` makes a pure, deterministic status/format/privacy/timer decision. Status priority: Invading > Searching for invasion > In Team Duel / In-duel > Spectating > Downed > Fallen > Hosting > In co-op (N out of 5) > Solo hunter. It supports a **future validated** location/level/build/boss snapshot, explicit privacy flags, fight start vs session uptime and bounded text. Unsupported/unknown data is not fabricated.
- **Integrated now**: existing `bbport/gpu/bbcoop/discord_status.cpp::ActivityJson` uses the production pure policy with current party, `bbcoop_duel_view`, `bbcoop_invasion_view`, local spectate/death observations. Existing joins/Discord party size remain, but a real invader cannot advertise the visited team's join secret. Per-field future opt-in environment flags are recognized; location is on unless `BB_DISCORD_SHOW_AREA=0`, level/build off until a verified game-data adapter exists. This is a policy/UI format integration, *not* a real runtime observation of stats or boss names yet.
- New `emulator/src/core/ultimate_pvp_faction_rules.h`: **standalone server/game-side policy candidates** for same-faction (and same-invasion-id) roster visibility, only same-side invaders reviving Downed bodies by server-verified hit, DBNO OFF => disconnect individual invader on lethal hit; DBNO ON => down if team has alive member, otherwise disconnect all active invaders on full wipe. Includes explicit global+host permissions and session capacity gate. **Not wired to the live shadNet/server** and does not claim new invader slots exist. Never send hostile private vitals to the other faction: visual hiding alone is insufficient.
- Tests in `bbport/tests/test_discord_activity.cpp` and `emulator/tests/bloodborne/test_ultimate_pvp_faction_rules.cpp` cover status priority, precision/privacy, timers, cross-faction and wrong-invasion rosters, partial/full invader wipe, own-faction attack revive validation, leader/global kill switch and team cap.

## External sources actually checked
- [Discord official Rich Presence](https://github.com/discord/discord-api-docs/blob/main/developers/discord-social-sdk/development-guides/setting-rich-presence.mdx): distinct details/state, party sizes, timestamps, optional assets and secrets. A single displayed start timer means fight timer takes priority while a fight is active; restore session timer after.
- [erezeth/bloodborne-rpc](https://github.com/erezeth/bloodborne-rpc): separate read-only offline-first stat, area and boss companion with unverified coverage. Its README states it intentionally stays out of co-op mode by default; do not run two IPC publishers or assume this companion's RAM offsets work on every CUSA/build. No source copied.
- [CLSAMG22/BBSC releases](https://github.com/CLSAMG22/BBSC/releases): notes on boss name/timer/build and dead/spectating status (different release/package). Candidate for **source audit** prior to adapting.
- `docs/DUELS.md`: current own team duels already distinguish team and free-for-all; not all PvP is an external invasion.

## Still unimplemented / hard gates
1. Game-thread validated local stat snapshot (level, STR/SKL/BLT/ARC at >=18), privacy-aware localized map name and boss table from exact CUSA 1.09 runtime; boss-fight start timestamp via verified event. No raw game memory reads from the RPC IPC thread, no artificial/placeholder names or fake live timer, no second Discord publisher.
2. **Multiple invaders**: server's single-invader admission, routing, invitation, session ownership, life-cycle and `InvasionEnd` have to be versioned for groups of invaders. Change server/game/client protocol atomically, maintain 5 *total* participants, host opt-in and global kill switch, and ensure rescues only between invaders of same live invasion. Matchmaking fairness and disconnect/reconnect race handling.
3. Defender and invader distinct HUDs: filtering must occur on server-authoritative stream as well as client, never expose enemy roster via compass, map, spectate or Discord. Show connected fallen players with empty HP until actual disconnect, including wipes. Maintain separate player vs invader DBNO settings (current co-op 'Go down' vs 'Spectate' is NOT the required PvP DBNO toggle).
4. Windows native build + actual Discord client screenshot tests, 2–5 real players, actor hit-to-revive, latency and spam benchmarks. No Fornex production deployment or game/save edits.

B56 is a **Draft source-level increment**, not completed multi-invader gameplay. No copyrighted game/third-party assets bundled.
