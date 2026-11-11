# Ultimate B82 — make reliable game-link resend membership O(1) without changing packets

Date: 2026-11-11. New stacked Draft on B81 #147, playable Ultimate scope. Shared production header `server/coop/game_link.h` is compiled by BOTH emulator client and shadNet server via `emulator/src/core/bloodborne_game_link.h`; it is not the independent no-eboot native Windows port.

## Source-established performance issue

`GameLinkPeer::Flush` emits queued native packets, then scans all unacknowledged reliable entries for due retransmissions. For each due retransmit the previous implementation called `std::ranges::none_of(entries, ...seq...)` on *every entry already selected for this flush*. During a frame hitch and reconnect, thousands of fresh reliable packets and up to `max_resends=64` older due retransmits cause repeated linear scans over the fresh outbound list. This is avoidable CPU work on the real-time network thread, including on the game side. The existing game-side reliable ordering, ACK, backoff, quiet suppression and capped resend count are otherwise sound and should be retained.

## Correct production change

- In the actual shared `GameLinkPeer::Flush`, track emitted reliable sequence numbers with `std::unordered_set<u32>` (expected constant-time membership). Add every fresh reliable sequence to this set before its move into `unacked`; when an older reliable packet is due, only retransmit it if `emitted_reliable.insert(seq).second` succeeds.
- Preserve the precise **contents, sequence numbers, ordering and frame packing** of all fresh reliable and unreliable packets, resend oldest-first, max 64 per flush by default, exponential resend backoff, keepalive and ACK semantics. `GameLinkPeer` remains a single shared client/server implementation; no new client/server protocol version, transport, settings or authentication change.
- **Critical safety review:** initially explored dropping older unreliable packets within the same channel, but stopped before creating a PR because `server/coop/packet_routes.h` confirms channel `0x04` carries enemy positions. Two packets on the same channel can describe *different enemies*, not the same stale state. The old implementation intentionally delivers in-order arrivals; merging by channel could break gameplay. This rejected candidate is **not** in the final PR. `server/tests/test_game_link_resend.cpp` and the real emulator GoogleTest now assert every one of 25 distinct same-channel enemy packets survives transmission.

## Deterministic tests and expected benefit

- Source contract runs under Linux and Windows.
- Production `GameLinkPeer` compiled **and executed** under GCC, Clang and MSVC. A deterministic synthetic frame hitch queues 100 old reliable entries (original frames lost) and 1,000 fresh reliable messages. The next flush must produce exactly 1,064 entries: 1,000 new in their original order followed by the 64 oldest retransmits; the following flush must emit exactly the remaining 36 old ones, with no immediate early duplicates. Another regression with `resend_ms=0` proves fresh reliable packets are not sent twice.
- Real GameLink GTest source covers loss/rejoin and 2/3/5-member synthetic cases; B82 adds a stress case for fresh+resend ordering, an enemy update preservation test, and the zero-delay corner case. A separate CI job syntax-compiles that real GTest with GCC and Clang.
- Complexity improvement is from repeated O(entries) membership searches for each due resend to expected O(1) checks. This saves proportional CPU work when queues accumulate; there is **no measured latency reduction** or FPS/ping claim without an actual Bloodborne 1.09 2–5 player rig and before/after network timings.

## Non-goals and safety

No full shadNet deployment, real gameplay test, server data migration, Fornex restart, game asset distribution, character savedata edit, release build or true independent native Windows executable. This packet path does not solve unresolved P0 #137 durable phantom key rewards or P0 #35 delayed native item-lots. Feature requests for launcher, RPC, controls, graphics, chat and PvP remain in the canonical requirements; their integration is selected by source-backed compatibility, tests and measured benefit rather than blind cross-repo merging. Existing external candidate PRs (Yharnam Together #577/#575/#574/#571 and droogie/bbhost #236/#221/#231) still require ABI and license evaluation.
