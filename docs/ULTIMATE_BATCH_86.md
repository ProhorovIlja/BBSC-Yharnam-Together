# Ultimate B86 — keep the team's world flags out of a guest's solo save

Date: 2026-11-11. Base: B85 `feda09ba67e31e7e9debe57bba38e4edbdfa5e17`. This is **the existing playable Yharnam Together Ultimate client**, preserving its co-op protocol and the existing transport fixes B82–B85. No original BBSC Bell matchmaking and no native-port switch.

## Verified upstream evidence and actual source comparison

**Source:** [official Yharnam Together PR #553 (merged)](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/553), specific files `emulator/src/core/bloodborne_team.cpp/.h`, `bloodborne_flags_store.cpp`, `bloodborne_server_world.cpp`, and `test_bloodborne_team.cpp`. Related earlier user reports of independent progress and an upstream game-rig demonstration are not proof that our Ultimate build has passed the game scenario.

**Observed pre-B86 gap in actual Ultimate B85 code** (also recorded in [P0 upstream source parity](ULTIMATE_P0_UPSTREAM_SOURCE_PARITY_20261111.md)): `SetGuestWorldChanges(bool keep)` can apply queued changes even when the guest now plays alone, and the existing `KeptChangeYieldsToTeam` only handles some team story steps in blocks already reported by the server. Changes to boss, door, lamp and other team-owned world flags could then be set in a different character's personal world. B64 separately imported a pure HomeWorlds policy but **did not integrate** the whole #554 live host-save migration.

## B86 implemented change

1. `bloodborne_team.cpp/.h`: pure `KeptChangeStaysWithTeam(flag, team_mode, plays_in_team)`, based on upstream #553, uses existing `IsWorldFlag` classification. A team-enabled save playing outside its team holds **only host/shared world flags** (except personal pickups and reset-on-load flags), not player-owned flags.
2. `bloodborne_server_world.cpp` and `bloodborne_re_internal.h`: `SavePlaysInTeam()` checks `team_switch && !team_party.empty()` under `team_mutex`, matching upstream's active-party semantics. Team mode enabled is not the same as active team membership.
3. `bloodborne_flags_store.cpp::SetGuestWorldChanges`: check the world-only hold condition **before** the existing `KeptChangeYieldsToTeam` fallback and, crucially, before the native event flag setter. Keep those changes in the queue for later in-team use; do not erase/tombstone them. Existing player-specific flags still take the original path, and writes still use the pre-existing atomic/worker-retry system.
4. `test_bloodborne_team.cpp`: game-native GoogleTest covers map boss/door flag 12401800, lamp 12407810 and story step 7240, versus character gesture 6744, gift 12101022 and pickup 52800170, plus active team/solo transitions.
5. `tools/ultimate/test_batch_86_solo_guest_world.py` and dedicated CI: source-call-site integration contracts, actual classifier conditions, locked membership read and no mutation/erase on hold. GCC/Clang and MSVC compile **the actual production predicate extracted by parser** with a **controlled stand-in** for `IsWorldFlag`. This is a useful gate but **not full game/emulator integration**; the production GoogleTest source is checked for coverage here, not executed unless the full `shadps4_bloodborne_test` CMake target is built.

No network-wire change, forced FPS/renderer flags, extra per-frame I/O, save deletion, or deployment. Additional team-mutex query occurs at the existing guest-world-change processing rate; benchmark if the call site is hot.

## Acceptance gaps / retained P0s

- P0 [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22): real 2/3/5-hunter scenario guest visits host at different boss/lamp/quest steps, leaves team in play and loads alone, verifies personal story flags unchanged and returning to team restores team changes. Rig must distinguish this from ongoing [#554](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/554) host home-world issue.
- P0 [#137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137) and [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35): guest-earned unique badge/tool and deferred boss/NPC grants still require safe persistent journal and game **save-file acknowledgment**, no cross-slot or duplicate grants.
- P0 [#73](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/73): official [#566](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/566) reapply guest's own picked flags **before** a rejoin baseline, with safe identity/slot-switch guards. Not part of B86.
- Run a whole-client Windows build and full actual `shadps4_bloodborne_test`/game rig before marking this a user-visible fix. CI extracted-native checks do **not** establish this.
- Private Discord screenshots, historical chat files and private Drive links remain in the account-specific gungrain handoff, not on public GitHub.
- No write or restart on production Fornex; no actual Bloodborne player saves, game files or user VPS touched.

## Search and cross-source provenance

[Detailed B84 global GitHub/Drive census](ULTIMATE_GLOBAL_SOURCE_SWEEP_20261111_B84.md) includes enumerated 586 upstream branch names and our YT/Windows-port branches, BBHost/visy/Nightwatch/BBGL forks, PRs and both Google Drive accounts. This B86 improvement uses actual upstream **patch contents and a precise difference against our current implementation**, not a first-result name-only selection. Full source review of all GitHub branches or every internet page is **not** claimed.
