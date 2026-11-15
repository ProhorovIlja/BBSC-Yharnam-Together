# Yharnam Together Ultimate: baseline and hybrid transport

Status: experimental decision and executable model, not a release or a deployment.

## Baseline

Keep the existing Yharnam Together fork as the product and compatibility baseline (launcher, bell-free teams, shared world, server/account flow). Do not change production Seamless Hunt, account storage, URLs or client/update channels. Maintain the native runtime as a separable donor/integration track, not a protocol replacement. Windows, Linux and macOS are native product targets. Runtime acceptance remains platform-specific and incomplete; see PLATFORM-TIMING-STORAGE-20261115.md for the updated target contract. macOS is no longer deferred as a product goal.

GitHub compare on 2026-11-14: fork main and experiment/ultimate-batch-93-gpu-use-range-bounds-20261111 diverged (B93 +933/-218 commits, 300 files returned, not an exhaustive diff); merge base efa0ad265d840d9195e55db2e3216f46f7daedd0. Do not promote the highest-numbered branch or wholesale-merge it. On the candidate, verify the behavior and ancestry of upstream PRs #554 (host solo world rollback and update save preservation) and #548 (phantom key item persistence). Existing fork regressions: #22, #35; historic v1.3.1 intake #76; presence #119; launcher CI #122; donor integration #130. Treat existing branches and issues as input, not as proof a fix shipped.

## Donor intake

- Amanises-Yharnam-Together/BBSC-Yharnam-Together: product upstream, team and world semantics, regression baselines. Its native port docs already describe Supermedo/AdrianCsT ancestry; avoid reimporting the same code.
- shadps4-emu/shadNet and Wozzardman/shadnet-p2p: compare transport, signaling and auth mechanics. Wizard's experimental mode is documented as bell-based; do not replace YT team flow with it.
- mark3317/bbgl + mark3317/bbsc-gl: Party LAN/VPN discovery and local coordination, native UDP, reconnect/NG+ and guest rewards. Upstream documents no host migration; no launcher game downloader import.
- droogie/bbhost, deadinside28/bloodborne_pc, Supermedo/bloodborne_pc and visy: runtime, renderer, packet-path and performance candidates, not a backend swap. visy server source not verified in this pass.
- Awakenchan/LanternEngine: launcher, Vulkan and Linux compatibility candidates. vladtepes22/NightwatchCoop: host flow and private connectivity diagnostics.
- Intake must record exact commit/PR, file license and attribution, dependency cost, baseline overlap, reproduction and independent tests. Public visibility does not imply reuse permission. Only legal local game dumps for testing; no game content, player records, secrets or private Drive archives in GitHub.

## Routing policy

Public authority validates membership, role, travel commits, boss outcomes, item/reward receipts and persistent world changes. Merely relaying a packet does not make its contents authoritative. The authoritative stream has bounded queues, idempotent operation IDs, room/area/visit epochs and slot ownership checks; transient failure cannot trigger a peer-only write. Unknown message classes stay disabled for the new path. Pose/visual updates are the initial direct-eligible classes, not damage or progression. Negotiate support and user policy first; require authenticated bidirectional path proof, keep relay as fallback, preserve ordering/replay state across paths, and use hysteresis. For strangers/invasions, default relay-only to avoid disclosing endpoints. Reconnect invalidates old membership and stale epochs. Test loss, reordering, duplicates, asymmetric NAT/CGNAT, port rebind and relay outage; no claims of zero latency.

Private LAN/VPN: discover on selected local interfaces with manual endpoint fallback for overlays that do not pass discovery broadcasts. Host is the local authority in-process or launcher-managed; no separately administered VPS/account. Explicit trust boundary and independent local saves; host departure ends the session until migration is implemented and tested. Never mix local-only state into public progression.

## Presence and stats

Discord local snapshot only, no game-thread IPC. Display location; compact second line `BL 25     STR/ARC` (exact rendering requires Discord desktop validation). Inclusive 18 threshold on STR/SKL/BLT/ARC; one qualifying stat uses full English name, exactly STR+SKL is Quality Build, other combinations abbreviate in stable order. Hide the build if none qualify or the snapshot is invalid. State: Hosting, In co-op, Invading, Spectating, or Fighting <boss>; occupancy uses negotiated team capacity and must not be repeated if native Discord party size already renders it. Invasion count must be faction-appropriate. One elapsed timer: boss start while actively fighting, otherwise original session/play start; reset boss timer on a new attempt, not on refresh or reconnect. Boss hook coverage, app registration and real client layout need validation; use existing #119 implementation rather than a second publisher. Independent opt-ins for detailed website telemetry and Discord; no IPs, coordinates, account IDs or private vitals in public feeds. Derive public occupancy from server session state, not client claims.

## Integration gate

1. Pin exact source and binaries for the reference client/server; snapshot schema compatibility without exporting real data. Use an isolated endpoint and synthetic accounts/saves. Prove #22 and #35 across host/guest, disconnect, crash, rejoin, DLC and five slots. Never roll back a stale save over a live one.
2. Wire the routing model behind a disabled-by-default flag. Compare relay-only versus hybrid at 2, 3, 5 players: p95/p99 latency, jitter, input-to-peer update age, failovers, server egress, CPU/RSS, and client frame time. Require no regression in authority invariants and report measured deltas before changing defaults.
3. Reuse the launcher for release channels, manifest verification, atomic update/rollback, game-folder validation, compatibility diagnostics and crash reporting. Add Exit to Desktop via normal shutdown, including session detach and save flush, not process kill. Reimplement historic save/cheat tools only offline with isolated profile, backup and public-session block. The archived v1.3.1 notes are evidence to investigate, not evidence all tools already work.
4. Build Windows/Linux game-free CI plus two real installations before public promotion. Measure shader stutter, low-percentile frame times and startup separately; isolate rendering patches from network/save changes. Production compatibility and a rehearsed rollback are gates, not implied by source tests.

Run the acceptance model with `python3 -B tools/ultimate/ultimate_hybrid_policy.py`. The six tests are synthetic; they do not exercise real packets, Discord, saves or a live game.
