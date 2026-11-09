# Ultimate B37: Hunters Online without blocking the launcher or inventing players

**2026-11-09**, stacked on [Draft B36 #83](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/83) with its real Windows/Linux Python CI 3/3 green. Related issue [#85](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/85).

The owner requested a compact visible **Hunters Online** count, asynchronous server/port checks and accurate TLS diagnostics for the Ultimate launcher. This batch implements **the first useful, source-backed component**: a global directory connected-player count in the Tk footer. Port-by-port diagnostics and local-host counts remain separate because the existing local `/status` endpoint has no authoritative game player count.

## Source proof for this exact count

- `server/src/link_server.cpp::Heartbeat` sends `count=m_link.Members()` to the sharded region directory; this is the count of **connected link members**, not proof the players are actively fighting in a game map.
- `server/directory/directory.py::GET /v1/shards` publicly exposes only **healthy** shard rows (names, counts and capacities); stale shard rows expire after 10s without a heartbeat. This is appropriate for an anonymous global aggregate.
- `server/src/webapi_server.cpp::GET /status` returns `ok` and service name only, **not a player count**. The old standalone launcher already probes game backend 20443, Link TCP and WebAPI, but the co-op distribution currently only checks the local host's running state. This batch does not conflate port reachability with game registration/auth.

## Real code changes

1. `bbport/launcher/bbport_coop.py::hunters_online(settings,fetch)` only contacts a **validated HTTPS** global directory URL at `/v1/shards` via existing checked-SSL `urllib` (with truststore support where available). It returns only `{'hunters':N,'shards':M}`, never IDs/IPs, and returns `None` for non-directory WebAPI, local-only host, network/TLS failure or malformed response. Valid `{'shards':[]}` returns 0.
2. Validate all shard names and integer counts (no bool/negative/floats/string numbers), reject duplicate shard names or overly large results instead of showing a misleading number; count only the directory's **healthy** shard list.
3. `bbport/launcher/bbport_launcher_win.py` includes a small plain-text **Hunters Online: — / Охотников онлайн: —** label in the co-op footer. First background check begins after the launcher starts, subsequent checks no more often than 45s through `coop_watch_server`, which already runs every 5s for the local host line. No blocking network operations on Tk thread.
4. Switching from one global server to another or from global to local immediately clears the old count. An older in-flight response cannot overwrite newer state: the result callback compares the immutable server setting key and respects launcher teardown. A failed request yields dash, not 0 or last stale value.

## Tested scope

New `bbport/tests/test_hunters_online.py` imports the **actual** production `bbport_coop.py` with fake HTTPS directory answers and asserts positive/zero/unavailable, two shards, malformed/negative/duplicate/huge values, local-only avoids network, invalid HTTP and URL rejected, failures and secret-free response. Source control ensures Tk thread offloading, 45s poll and stale-key guard. CI on Windows 2022 and Ubuntu 24.04 plus exact six-file B36 source delta and three blob hash pins.

## Remaining issues

- Port-by-port link/backend/WebAPI health for a selected remote server, manual refresh, TLS certificate chain details, clipboard-safe support diagnostics and more usable UI [#85](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/85) [#24](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/24). These must use verified HTTPS and genuine protocol/health tests; a single TCP SYN is not full authorization success.
- Local server counts remain unknown because the existing `/status` doesn't expose them. The UI deliberately shows dash.
- Other game CUSA compatibility [#84](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/84), optional host-controlled spectators [#86](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/86), reorganized settings [#87](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/87), hybrid direct P2P [#80](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/80).
- Game GUI not run or visually inspected on a real Windows machine, no network load test, no Fornex changes, no private assets or savedata. Draft only.
