# Ultimate B39: accurate Hunters Online on a local or friend's ShadNet server

**2026-11-09**, stacked on [B38 Draft #90](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/90). The owner requested the previously delivered B37 **global** Hunters Online counter also work for **Local** servers hosted on the PC or joined through Radmin/LAN.

## Source-proven problem

- `server/src/link_server.cpp` actually owns signed-in UDP link membership via `m_link.Members()`. In hosted mode its heartbeat already posts `count=m_link.Members()` to the global region directory, which B37 aggregates. But a single local host may have no directory.
- `server/src/webapi_server.cpp::GET /status` currently says only `ok` and `service=shadnet-webapi`, so a launcher cannot infer its link player count from `/status` or simply testing an open port.
- `server/src/client_session.h::SharedState` is visible to both the LinkServer event loop and the WebAPI listener. Its existing `usageTotalOnline` counts a **different connection type** (authenticated ShadNet PSN sessions); using that would give a misleading Bloodborne team population.
- In B38 the launcher global count is server-keyed but local still returned unknown. Owner wants 0 to 5 (or actual player count) from his hosted local friend's server, not a guessed zero.

## Real server and launcher changes

1. `SharedState` gains `std::atomic<int> linkMembers{0}`, a single aggregate counter without identities. `LinkServer::Apply(const ServerLink::Hub::Result&)` sets it to `m_link.Members()` after applying linked/gone events. Atomic relaxed order is adequate for an approximate-read, tear-free value in WebAPI, with no World/Save lock and no per-player data.
2. `WebApiServer::GET /status` adds `"link_members": N` to existing `ok/service` JSON. This provides anonymous public local ShadNet status and preserves the existing response structure used by older clients. Zero is verifiable if the server is running and truly has no Link members.
3. `bbport_coop.local_hunters_online(settings)` queries exactly the selected **Local** `host_ip` on `http://host:31315/status` with 4s timeout, max 1024-byte body, no proxy and no account/password/key headers. Reject invalid host, URL path/userinfo/fragment, unsupported server, missing count, bool/float/string/negative/huge counts. Returns `None` so launcher displays **—** until it contacts a B39-aware server. Do not disable online login's certificate verification; this anonymous local HTTP endpoint is separate from global HTTPS auth.
4. Co-op footer now selects the B37 Global directory helper for global mode and B39 local helper for local mode. Local host change invalidates old result and triggers new background check every ~45s. Online count remains **signed-in Link members**, not guaranteed active combat participants or real-human unique count.

## Verification

- `bbport/tests/test_local_hunters_online.py` imports the **actual production** `bbport_coop.py` and tests 5 link members, true zero, old server without field, malformed response, wrong service, timeouts, invalid host and bounded data, and source server/UI wiring with real C++ code locations.
- Windows 2022 and Ubuntu 24.04 Python tests plus B37/B38 regression tests.
- A **full isolated Qt6/protobuf shadNet server build and its in-tree CTest suites**, using the established `server/hosting/Dockerfile --target verification-tests` workflow from B27, catches incompatible C++ atomic/HTTP modifications. Do not call this green until actual CI confirms it.
- Exact nine changed paths and six SHA pinned source/test blobs compared to B38.

## Limits and pending

Remote port status diagnostics (TCP/UDP health) remain [#85](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/85). Pure TCP connect does not prove the UDP game or co-op login works. In a default local setup WebAPI 31315 may be blocked by the host firewall even when game traffic works; count will be unknown, never misrepresented as zero. The anonymous local health endpoint is **HTTP** (not login, no sensitive fields); all Global profile/add account operations continue to require certificate-verifying HTTPS.

No live Fornex, game executable, save, private contents, production deployment, installer or multi-client physical game test. Keep Draft.
