# Ultimate B12: do not request guest character data before its network slot exists

**Target:** playable Yharnam Together 1.4.0 hot-join / map-travel resilience. B12 is stacked after B11 #43. Experimental runtime-source change, not a playable Windows installer.

## Verified 1.4.0 source-level failure opportunity

The earlier YT join code correctly rebuilds individual remote join tasks and tracks each pending player separately. In `emulator/src/core/bloodborne_boards.cpp`, `FinishWaitingJoins` resolves a specific guest's online identity against the vitals board. However, it previously called `MemberDataWait::Tick(now, member_here, parts ? ReadValue<u8>(parts,0) : 0)` even when `MemberDataSlot(net, member_id)` found no network/data slot, or `MemberDataPartsAddress` returned null because the received-parts byte could not be written.

When the board already says that a remote hunter is standing on this map, the one-second settle elapses, and Tick emits `Request` **despite an invalid/missing net or slot**. The caller then invokes the game's `NetSyncSendOffset` with that net pointer. The request can have no usable parts byte to clear, and the code cannot establish that the request belongs to a fully provisioned per-member data slot. This is a source-level hazard around loading, reconnecting and late joining, not a reproduced crash or claim that it is the sole cause of an invisible player.

The original upstream Amanises YT 1.4 source was compared for the same call site and also passes `here` independently of `slot`/`parts`. The local tree already contained a **per-member identity** correction (compared with the older broad any-member presence check), which B12 deliberately preserves rather than duplicating.

## Code change

- Add `MemberDataRequestReady(member_here, slot, parts)` to `bloodborne_party.h/.cpp`: permits only a member currently on the map, a valid remote receiving slot **0..3**, and a writable per-member received-parts byte at a valid address. The caller's `MemberDataSlot` already checks the net object memory and matches the **exact member ID**; `MemberDataPartsAddress` validates write access.
- `FinishWaitingJoins` passes this guarded readiness to its existing `MemberDataWait::Tick` state machine. If the slot disappears, its waiting/request timer resets; when the correct slot returns, it must settle and request **fresh** data again before creating the remote actor. This avoids sending a request with a null/incorrect network object, and does not use bytes from an earlier map as a new answer.
- Existing `SendMemberDataRequest` packet format, session identity, network transport, server code, DBNO, five-player capacity and character creation remain **unchanged**. Normal ready-slot flow sends the exact same message.

## Tests

- Additional **real GTest C++ cases** in `emulator/tests/bloodborne/test_bloodborne_member_data.cpp`: board name/HP visible without slot, no writable parts byte, slot drops after a request, recovery requires a fresh reply, and all four remote receiving slots in a **five-hunter session**.
- `tools/re/tests/test_member_data_slot_guard.py` compiles the **actual production** `HasAllMemberData`, `MemberDataRequestReady` and `MemberDataWait::Tick` C++ definitions directly from source and executes synthetic two-guest/invalid-slot/slot-recovery scenarios on Linux and Windows CLANG64. It also verifies exact callsite wiring to guarded received-parts reads and the original network/slot lookup invariants.
- Dedicated B12 CI checks only the **eight permitted file changes**, pinned source/test Git blobs, production helper compilation on both operating systems and existing B01–B10 source regressions. No full native Windows renderer/game build per patch.

## Limitations and remaining release gates

This is a preventive state/slot validation fix, **not yet demonstrated** to solve the Hunter's Dream missing-body report. A real game has other possible causes: destroyed remote actor, false session identity, replica map instance, delayed join tasks, sign-in identifiers, stale user saves or server matchmaking. Verify on Bloodborne 1.09 with 2/3/5 players, a host already hunting, Hunter's Dream, host/guest alternate map travel, disconnect/reconnect, DBNO and downed characters, active invasions, and full server Link4. The real game may use memory layout conditions that synthetic C++ tests cannot reproduce.

No proprietary Bloodborne/DS3 files, passwords, saves, installer, live Fornex or public binaries are read, modified or uploaded. B12 is a Draft source candidate and requires integrated Windows #31 compilation, source compatibility and gameplay QA before promotion.
