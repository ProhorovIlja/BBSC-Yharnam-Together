# Ultimate B65: inspect and adapt our other Bloodborne PC Windows port

Date: 2026-11-10. Parent: [B64 Draft #129](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/129). Tracking: [#130](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/130). **Actual code change plus test, not a completed runtime merge.**

## Why this repo matters

The user owns [ProhorovIlja/bloodborne_pc_windows_port](https://github.com/ProhorovIlja/bloodborne_pc_windows_port), verified master commit **6486642d35418bd26c278bceadaf42e842daf4e4** (2026-11-08 latest push at inspection). It is a fork of `visy/bloodborne_pc_windows_port`, traced back to `deadinside28/bloodborne_pc` and includes work based on Mrsuss60, Supermedo, droogie/bbhost, shadPS4 and others. Its current README calls it v0.7.2 and describes running original Bloodborne 1.09 ELF via Win32/HLE + Vulkan. **It still needs decrypted `eboot.bin` to start**. That is not our separate true *no-eboot* AOT Windows goal.

Additional source documentation: [patches for forks](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/blob/master/docs/PATCHES_FOR_FORKS.md), [two equal missions](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/blob/master/docs/SEAMLESS_HUNT_TWO_MISSIONS_MASTER_SPEC.md), [PC/Windows port README](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/blob/master/README.md), [save safety](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/blob/master/docs/SAVES.md). Existing AOT [port PR #84](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/84) and YT hybrid [port PR #85](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/85) are **OPEN Draft** at audit. Do not falsely claim a fully standalone shipped AOT build or verified hybrid protocol.

## What B65 ACTUALLY imports

Compared `scripts/game_check.py` of the pinned external master (sha at audit) with our own production `bbport/scripts/game_check.py` (not byte-identical). **Our code already supports the nine retail CUSA title IDs and original image hash**; those were not imported twice.

Specific external code adapted into **actual** Ultimate:
- `readable_and_broken(path)`: when an antivirus or sync tool temporarily denies a shader-file read, log it and do not kill preflight with an unhandled exception. It is still an **unchecked shader**, not proof of intact data; actual load could still fail. Inherited from Supermedo/bloodborne_pc PR #64 via the user's port.
- `_pass_key` + optional `problem(..., cache=path)`: cache a **successful** preflight by file size, mtime and directory/relative path, avoiding repeated hashing/decompression when the caller explicitly opts in. Improvement over the external implementation: use full *relative paths*, not just `f.name`, to distinguish shaders with the same basename, and never use the cache when an independent `image_hash` is supplied. Inherited `BB_SKIP_GAME_CHECK` behavior unchanged. **Default runtime still performs full checks** because `cache=None` by default, and no launcher auto-enables caching yet. File metadata is not a cryptographic proof: changes with spoofed size/mtime could be missed; revalidate when repairing/updating files.
- `eboot_clean(game)` and its explicit `UNCLEAN_EBOOT_EFFECTS` warning: independently check clean Bloodborne 1.09 image even if the general game-check bypass is set. Returns True/False/None; does not edit executable or saves.
- `bbport/tests/test_game_check.py`: new positive cache, changed image, independent-image-hash override, malformed cache, locked DCX and clean/unclean/invalid `eboot` regression tests using **synthetic fixture content**, not any player's game files.

## Cross-project architecture matrix (verification level explicit)

| Area | Source repo | Present in our Ultimate B64? | Decision |
| --- | --- | --- | --- |
| Game version/hash/9 CUSA | `scripts/game_check.py` | Already present; changed preflight logic missing | **B65 adapted** narrowly and regression-tested |
| Dedicated bbport save segregation | `scripts/party_saves.py`, `src/runtime_savepolicy.c`, `src/save_policy.h` | These *exact files* absent from Ultimate's `bbport/` subtree | **Research P0**. Evaluate game-save namespace and rollback before **any** standalone runtime mode; do not overwrite YT profiles |
| P2P/NAT and authenticated party networking | `gpu/shim/party/party_nat.cpp`, direct peer suite, `scripts/party_env.py` | Exact source paths absent from Ultimate `bbport/`; Ultimate runs YT/shadNet online | **Candidate**. Data-plane protocol/transport, NAT tests, 5-hunter save/authority tests; no direct wire compatibility assumption |
| GPU optimizations / crash and high-FPS stability | `gpu/shim/bbport_stability.cpp`, `gpu/shim/bbport_stability_logic.h`, renderer | Exact source paths absent from Ultimate `bbport/` | **Candidate** only after exact patch-site checks, Vulkan renderer ABI comparison and A/B frame times on same hardware |
| Character progression / bosses / chalices | `gpu/shim/party/*.cpp`, `patches/Bloodborne.xml` | Different game hooks; our `emulator/src/core/bloodborne_party*` exists | **Do not bulk cherry-pick**; inspect verified 1.09 CUSA offsets, persistence, item duplication risk and code owners |
| One Ultimate launcher, interchangeable backends | `launcher.py`, `launch_gui.bat`, `run.bat` | Our YT server/launcher path exists | **Separate isolated runtime profile** can be added only after valid installation/launch and saves-isolated transition tests; never silently create incompatible hybrid sessions |
| Fully eboot-independent Windows game | Port Draft PR #84 and prior AOT stack | AOT code research separate from playable fork | **No**: tests/codegen partial, original PS4 ELF still needed by the playable port; no valid release without independent runtime boot & gameplay |
| Hybrid direct P2P fallback | Port Draft PR #85 (YT v1.3.1 baseline) | Ultimate now has more B64 changes and 5 hunter goals | **Re-evaluate protocol migration**, not automatic merge of an older Draft |

## Licensing and distribution gate

**Important:** GitHub reports the external user's port repository as **GPL-3.0**; Ultimate is GPL-2.0-or-later but previously introduced a separately attributed `GPL-2.0-only` boss-ID catalog in B60. **GPL-2.0-only + GPL-3.0-only is ordinarily incompatible for one redistributed combined program**. Even though both repos are under the user's account, upstream contributors retain copyright and conditions. **B65 remains Draft/source research only**, not a distributable combined binary. Obtain compatible licensing/permission or replace incompatible dependencies with independently legal sources before a release. A proper per-file provenance audit remains necessary.

## Global source search, bounded and cumulative

We also searched current `visy/bloodborne_pc_windows_port`, `deadinside28/bloodborne_pc`, `Mrsuss60/bloodborne_pc_windows_port`, `droogie/bbhost`, and the YT ecosystem. The user's other repo explicitly cites Supermedo, shadPS4, and Nightwatch co-op PRs. Search isn't equivalent to verifying *all* GitHub and all Drive content; record each tested change by exact file/ref, tests and conflicting license. The source index is a living registry, not a one-time claim of worldwide exhaustive coverage.

## Next gates

1. Verify B65 Win/Linux Python source tests and Windows native cumulative client separately. No use of private game assets in CI.
2. Evaluate the port's runtime and party save policies under new synthetic files **before** any launcher mode. Clean `eboot` digest/1.09 9-region parity must remain checked.
3. Review P2P direct protocol from the actual `gpu/shim/party` implementation in bounded file spans, compare to our YT/shadNet server, implement protocol negotiation, reliability/security/RTT benchmarks and fallback when worth it, **not merely overwrite one transport**.
4. Compare GPU/video, shader caches and load optimizations on identical game/driver/hardware and protect current performance; license/notice check per file.
5. Finish B64 HomeWorlds transaction migration and upstream #548 phantom key-item ledger P0 before any save switching.
6. Preserve native AOT mission independently, no `eboot` runtime dependence allowed for its final acceptance.
7. No Fornex production changes, real save access, code release, or game asset redistribution.
