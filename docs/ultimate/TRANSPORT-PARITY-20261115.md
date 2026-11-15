# Transport parity, measured resend work and source intake

Base: `d4db013cccf5ae3755c9d14908f9defb81b8a8ce` (PR #251).

## Integrated behavior

The active branch lacked the ACK-window protection and behavioral tests in the
earlier Ultimate [PR #150](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/150),
head `fc1a1e45164791c277879f078c11d1737e916fbe`, and the resend work from
[PR #149](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/149), head
`6a02cd809fac9446ee42de6900e6d31ae4793efb`. Both remain separate unmerged drafts.
The new code integrates the ACK behavior and real-header regression tests while
preserving the recent wrong-recipient, queued-visual and backup I/O fixes.

A cumulative ACK can retire only reliable sequence numbers actually emitted by
`Flush`, not merely queued ones. An impossible ACK does not suppress incoming
data. The sent limit resets with the reliable stream. This protects a network
retry queue; it is not an authenticated savedata acknowledgement. Sequence-number
wrap and authenticated rejection of retired remote runs remain separate gates.

The old resend loop repeatedly searched all packets already selected for the
flush. The initial PR #149 hash-index candidate was slower in the local synthetic
CPU comparison, so its implementation is not imported. Each outstanding reliable
packet instead records the flush that emitted its sequence. Membership is a
constant-time tag comparison with no temporary index or extra scan. This costs
one `u64` per outstanding outgoing record and one counter per peer. A counter-wrap
path clears old tags. Same-channel unreliable packets are all retained: they can
describe different enemies. Order, batching, resend cap, backoff, quiet-link
suppression, restart recovery and wire format remain unchanged.

## Executable checks

The standalone cross-platform CMake suite executes 18 existing/extended transport
GoogleTests, five resend/ACK parity scenarios, four restart scenarios and ten
world-preservation scenarios. The five parity scenarios come from PR #150's
real-header test. The future-ACK scenario reproduces a failure against the base;
the other parity cases preserve behavior rather than claim a new bug each.

`wire_transcript.cpp` uses deterministic packet loss, duplication and reversed/
delayed arrival for three settings, including a zero resend interval. Its outgoing
frames and delivered payloads produce the same recorded transcript digest as the
base. All reliable data is acknowledged before the fixed cutoff. This is a
synthetic protocol check, not a live multiplayer test or an authentication proof.

`bench_flush.cpp` measures only `GameLinkPeer::Flush` CPU time with 0/64 older
reliable packets and 0/64/1,000/10,000 fresh packets, 100 samples per case. Peer
construction and queuing are outside the timed region. Timing is diagnostic and
does not gate CI. Local machine scheduling and allocation noise affect results;
there is no game FPS, network RTT, server-load or latency claim. Compare the
baseline, discarded hash candidate and current implementation with the same
compiler/options and retain all runs, including no-resend controls.

Five paired runs, alternating implementation order, produced the following
medians of each run's p50 on this Linux x86-64 cloud host (GCC, `-O3 -DNDEBUG`):

| Older packets due | Fresh reliable packets | Base, microseconds | Current, microseconds |
| ---: | ---: | ---: | ---: |
| 64 | 0 | 2.594 | 1.793 |
| 64 | 64 | 9.083 | 6.810 |
| 64 | 1,000 | 89.181 | 59.267 |
| 64 | 10,000 | 945.211 | 687.362 |

These due-resend samples reduce this function's measured median CPU time by
25–34%. No-resend controls are retained separately, including a 1.84% increase at
64 fresh packets and effectively unchanged timing at 1,000. This does not predict
end-to-end game performance. The hash candidate is 97.924 microseconds in the
64-old/1,000-fresh case and is excluded from the final code.

The existing world/link CI runs on Linux, Windows and macOS. Server CMake also
registers the five-case parity executable. C-shim/transport sanitizer checks are
scoped to the compiled fixtures; no retail gameplay is sanitizer-tested.

## Cross-project intake (2026-11-15)

This is a focused source intake, not an assertion that all forks, branches or the
entire internet have been read. A merged upstream fix, local integration and
in-game verification remain distinct statuses.

| Source inspected | Evidence and current disposition |
| --- | --- |
| Ultimate #149 / #150 | Exact production changes and tests reviewed. ACK behavior integrated; resend algorithm adapted after measurement. Earlier branch workflows and unrelated changes are not imported. |
| Yharnam Together [#593](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/593), merge `1e85c5fc0e2919190e8c05aceddfede6931441ce` | Supermedo 1.9.8.5 crash/command-buffer/heap/dump-detection changes. Its notes still require executable fingerprints and byte checks. Candidate for targeted GPU/runtime validation; not enabled here. |
| Yharnam Together [#598](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/598), merge `63b578004acc43bb4d493e84031d89018b0687b6` | Linux BBport build/launcher integration. Upstream describes Windows checks and explicitly lacks a Linux playtest. Separate from this project's strict prepared-host runtime acceptance. |
| [deadinside28/bloodborne_pc](https://github.com/deadinside28/bloodborne_pc) | Its documented preparation maps a game image and uses a small runtime. Useful source for renderer/runtime adaptation; its use of native CPU execution does not establish our complete no-console-image runtime gate. |
| [Awakenchan/LanternEngine #102](https://github.com/Awakenchan/LanternEngine/pull/102), head `9cc2ff62dff48168d9b7a944c7cad18ae432bd43` | Unmerged Native+ HDR import from LRF17. Broad renderer/launcher change; its review notes lack a full engine build. HDR/shader layouts, device capability checks and notices need validation before integration. |
| [ayozetr/bloodborne_linux #53](https://github.com/ayozetr/bloodborne_linux/pull/53), head `156e0d6aee62a7cd1840b385455f7801b3964f1c` | Unmerged atomic LOD slot-claim guard with upstream synthetic/playtest evidence. Not a verified local fix. Requires exact-image byte/register checks and race-harness reproduction before adoption. |
| [macOS port #78](https://github.com/Wooloomooloo2/bloodborne_mac_port/pull/78), merge `0e4a9f3b73aeb1207329f130241d27ded8af1c8e` | Online-module provenance inspected. The optional network module runs in the x86-64 game process; the arm64 GPU host is separate. Its combined module includes GPL-3.0-or-later code and pinned third-party notices. It is not a drop-in arm64 game binary. |
| [droogie/bbhost](https://github.com/droogie/bbhost) | README describes runtime loading/relocation of the game's ELF plus host library implementations. Feature/runtime reference; does not itself meet our stricter runtime acceptance. |
| [Wozzardman/shadnet-p2p](https://github.com/Wozzardman/shadnet-p2p) | README describes signaling and a matching client fork on trusted private connectivity. Protocol/lifecycle/authentication compatibility must be verified before reusing its direct path. No VPN/network deployment made. |
| [vladtepes22/NightwatchCoop](https://github.com/vladtepes22/NightwatchCoop) | Current README advertises six-player seamless sessions, shared/personal lamps, travel voting and optional game-file conversion. Features are intake candidates; README claims are not local gameplay validation or save-format compatibility. |

No raw chats, game files, image-specific bindings or retail-derived assembly are
part of this public change. Dark Souls III folder discovery is not binary or
engine compatibility proof; no DS3 code/assets are substituted into Bloodborne.
