# Ultimate B60: game-thread boss gauge identity and encounter timer for Discord

**Date:** 2026-11-10. **Parent:** [B59 Draft #124](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/124). **Tracked:** #119, #9. Changes are Draft source-level work; **no production deployment**.

## Cross-project research and source corroboration

- The existing actual co-op client already reads and clears the game's **three boss HP gauge entries** in `emulator/src/core/bloodborne_party_death.cpp::ClearBossBarsAfterDeath` using `BossGaugesPointerOffset=0x05562878`, `BossGaugesOffset=0x1658`, `BossGaugeSlots=3`, `BossGaugeSize=0x14`. Its own `emulator/src/core/bloodborne_party.cpp::BossGaugesUp` treats a gauge's handle at +4 equal to -1 as empty and the note in `bloodborne_party.h` describes the name ID at +0, a shown byte at +0x10.
- Independently, [erezeth/bloodborne-rpc](https://github.com/erezeth/bloodborne-rpc/blob/main/source_code/main.cpp) uses the **same base pointer** and name/handle offsets, with **87** name ID -> boss/actor labels; its [README](https://github.com/erezeth/bloodborne-rpc/blob/main/README.md) explicitly states the author has NOT tested all bosses and locations and defaults to offline-only. The [catalog's license](https://github.com/erezeth/bloodborne-rpc/blob/main/LICENSE) is **GPL-2.0**. B60 copies/adapts the table **with credit in a separate `GPL-2.0-only` header**; no separate companion or competing Discord publisher is started. License compatibility for redistribution remains subject to final full-project review.
- Other Bloodborne mods/upstream Yharnam Together and the independently researched PC runtime provide boss gameplay and rematch comparisons, **not a guarantee that these 87 IDs work on every game region/build**. We never infer a boss from area alone. No proprietary game assets are imported.

## Actual code changes, not just a policy stub

1. **`emulator/src/core/ultimate_boss_names_gpl2.h`**: attributed 87-entry C++ boss/actor name catalog, with explicit `BossNameForId` and an empty result on missing ID.
2. **`emulator/src/core/ultimate_boss_presence.h`**: independent read-only decoder of the exact existing 3 x 0x14 gauge layout. Requires a non-empty handle, the shown byte (+0x10) and a known ID for **every active slot**; duplicate same-label IDs (e.g. Shadow of Yharnam's multiple bars) resolve to one name, conflicting known names or an unknown active slot fail closed. Does not read arbitrary memory on its own. Also provides `EncounterClock::Observe(active, map, unix_seconds)` that starts on the first observed *game-thread* active tick, retains the timer through phase/name changes, and resets on map change / boss end.
3. **Actual `PostVitalsAndPanel` in `emulator/src/core/bloodborne_party_death.cpp`**: if game-tick's existing `local_boss_fight` is true, reads the same already-understood boss gauge pointer with `HasMemoryAccess(..., MemoryProt::CpuRead)` and overflow guards, copies exactly 0x3C bytes, then decodes the name only if the scanner validates it. No write, hook or extra process. The `PartyDeathRun` `rpc_boss_clock` stores an independent encounter start.
4. **`emulator/src/core/bloodborne_party.h`**: extends the guarded, mutex-copied `PartyPanel` with `local_boss_name` and `local_boss_started_unix`.
5. **Real `bbport/gpu/bbcoop/discord_status.cpp`**: picks up the verified name and timestamp directly from that `PartyPanel`; removes the old `boss_previous` timer that started only at a 2-second Discord polling interval. Existing B59 policy continues to show `Fighting <Boss Name>`, `Watching <Boss Name>` for spectators, else `Boss fight` if there is no verified name. It retains permitted area, `BL`, compact `Build`, party status, independent privacy and timestamp fallback.

## Safety, QA and constraints

- **No guessed boss**: it is normal for some encounters to show `Boss fight`; there must not be a stale name after defeat, load, disconnect, boss bar despawn or unknown ID. Labels from the external catalog are **candidates**, not proof of compatibility with all nine CUSA 1.09 region builds.
- **No false victory**: a source-only C++ test and a Windows native compile do not prove that every boss, DLC, phase transition and Chalice encounter reads accurately at runtime. Test real save-isolated gameplay with 2–5 hunters and inspect captured Discord IPC/desktop output.
- **Game tick, not frame-perfect timer**: encounter start is the first `PostVitalsAndPanel` active observation (typically an ~1-second cadence); not the exact in-engine cutscene event timestamp. Boss death/reset and game reload must be checked. Keep `B59` existing fallback to play-session time when boss visibility is OFF.
- **Server and player privacy unchanged**: boss/level/build flags stay local, opt-in and are never transmitted to the game backend; no second publisher, no extra game hooks. Never expose join secrets in private sessions. Host/world saves and Fornex untouched.
- **Actual verification**: `emulator/tests/bloodborne/test_ultimate_boss_presence.cpp` covers all 87 unique IDs, common game bosses and DLC/Chalice variants, unknown/ambiguous/malformed/multiple slot observations, hidden HP bars, clock phase/map/reset. Dedicated Win/Linux source contracts + GCC/Clang C++20 build/tests, plus cumulative Windows game compiler CI. Real Windows game/Discord-run remains **pending**.

## Next work

1. Test exact 1.09 CUSA region behavior and observed gauge shown byte; if active bars on a supported build fail to decode, independently inspect engine UI bar state and implement a proven per-build adapter rather than guessing.
2. Boss encounter game event start/death/wipe timing, including spectate and rematch. Reject stale names with loading/wipe transitions.
3. Runtime test real `Fighting <boss> | <location> | BL 25 | STR/ARC Build` vs unknown generic, full IPC message, privacy field matrix and long Unicode boss names. The B59 `BBSC: Yharnam Together` asset hover is not a registered Discord application ID.
4. Continue P0 host-world rollback/key-item persistence fixes and multi-invader DBNO server/HUD networking separately. No Ultimate public release until all gates pass.
