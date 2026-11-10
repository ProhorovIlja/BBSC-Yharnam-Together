# Ultimate B69: real game phantom inventory identity guard

**2026-11-10. Parent:** [B68 Draft #133](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/133). P0 [#35 guest key items lost across game exit](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35). NO real saves touched and no in-game claim of durable debt recovery.

## Confirmed bugs in our source

1. In the actual game tick `emulator/src/core/bloodborne_travel.cpp::GiveBackPhantomKeyItems`, `static phantom_list`, `first_look`, `last_look`, and `own_look` were kept **across save-slot changes and across creation of a new character in the SAME slot**. The old key-list pointer and phantom-earned goods could then be interpreted in a different hunter's inventory, with incorrect grants or losses. This was a real source vulnerability, not a release repro.
2. [Upstream Yharnam Together merged PR #548](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/548) already connects a legacy `phantom_keys` slot file to its live game loop, so its `test_bloodborne_team.cpp` expected `phantom_keys` inside `CharacterSlotFiles`. **B68 imported that test expectation without connecting the on-disk side file**. That specific test would fail when compiled against our Ultimate, and adding a legacy file to cleanup prematurely would wrongly suggest that new-character lifecycle and durable debt are already wired. B69 makes the expectation reflect our real scope instead.

## Actual game code changes

- `emulator/src/core/phantom_inventory_scope.h`: small header-only C++20 `PhantomInventoryScope` stores the last observed `character_slot` (allowed userdata0000...0009) and `deferred_reward_character_generation`, and emits a change signal. Unknown slot, unsupported slot and uninitialized generation are **invalid**. It is used by the **real** game tick, not only a test.
- `emulator/src/core/bloodborne_travel.cpp`: `GiveBackPhantomKeyItems` reads the authoritative slot and new-character generation on each tick. When either differs, it immediately drops **only transient in-process phantom-list snapshots**: pointer, first/last observations, own-item baseline, and stale poll timestamp. It then refuses to use an invalid character identity. This guard runs before reading any game key-item list or granting goods.
- `emulator/tests/bloodborne/test_phantom_inventory_scope.cpp`: GCC, Clang, MSVC C++20 regression for all 10 legitimate slots, uninitialized/unknown slots, same slot new-generation, switching back and forth and identity unchanged. Cross-platform CI compiles the exact header included by the game hook.
- `emulator/tests/bloodborne/test_bloodborne_team.cpp`: corrects imported upstream #548's out-of-scope cleanup assumption: verifies the legacy file is not silently claimed to be lifecycle managed until its live persistence is wired. Maintains original upstream 5 state tests and B68 strict parser/restart cases.

**Important:** this guards unsafe cross-character in-memory transfers, but it deliberately does **not** clear the pending debt on a temporary network disconnect or ordinary loading; doing so would reintroduce loss before the B68 disk-backed recovery can be connected. That is a separate P0 game feature.

## Scope and remaining blockers

- B68 [immutable file journal](ULTIMATE_BATCH_68.md) remains **source/offline-only**. B69 is the first related modification to the **live** in-game phantom item callback, but it does NOT supply actual owed items after a process restart. The user-visible missing-key issue #35 is **not yet resolved**.
- No authorization to infer a 32-hex character fingerprint from a display name or slot alone. Need a stable, verifiable identity that changes when the hunter slot is reused.
- No correct guarantee to commit a debt-cleared tombstone merely on `AddTradeItems` returning: item grant in RAM must be followed by an authoritative saved game inventory checkpoint, followed by versioned debt ack. Until that handshake is implemented, **do not call the B68 `CreateNewRevision` on live player saves**.
- Current C++ tests validate real production header and static source contracts, not full emulator CTest/real Bloodborne rig. Native `bbport` Windows PE game-free build is separately monitored. Gameplay acceptance must include all nine CUSA 1.09 regions and 2–5 hunters, slot switch mid-coop, new hunter in same slot, guest quit, mid-write AV lock/disk-full, reconnect, boss drops and no duplicate rewards.
- Public combined Windows-port GPLv3 vs GPLv2-only catalog license issue still exists; no binaries/For­nex deployment/proprietary game files.

## Cumulative global source intake this pass

- [visy/bloodborne_pc_windows_port](https://github.com/visy/bloodborne_pc_windows_port) version **0.8.0** publicly lists direct P2P party, shader cache, frame pacing, 5/6 experimental party, inventory and save improvements; do not assume compatibility with YT/shadNet 5-player packets. Its merged [#16](https://github.com/visy/bloodborne_pc_windows_port/pull/16) documents CGNAT/double-NAT false-positive port status, [#7](https://github.com/visy/bloodborne_pc_windows_port/pull/7) fixes Radmin VPN `MappedAddr`, [#24](https://github.com/visy/bloodborne_pc_windows_port/pull/24) makes host authoritative for party size, and [#32](https://github.com/visy/bloodborne_pc_windows_port/pull/32) adds gameplay patch hashes to mod handshake labels. Each merits separate protocol-compatibility, license and test review; none cherry-picked here.
- [Supermedo bbport changelog](https://bbport.de/changelog/) now documents BBSC integration and explicit regional relay routing. It is not automatically compatible with our server or relay infrastructure. No production server changes.

No exhaustive all-GitHub or all-Drive coverage claimed. Track work in [cross-chat master](ULTIMATE_CROSS_CHAT_REQUIREMENTS_MASTER.md), [Issue #130](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/130), and private Google Drive handoff.
