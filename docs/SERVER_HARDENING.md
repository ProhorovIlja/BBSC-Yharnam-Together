# Seamless Hunt: Yharnam Together 1.4.0 server-only hardening

**Development branch, NOT a live deployment.** This work keeps the official Yharnam Together v1.4.0 client, launcher, protocol version, world format and auth identity unchanged.

## Source and scope

- Fork baseline: upstream release/main `efa0ad265d840d9195e55db2e3216f46f7daedd0`.
- Imported upstream [PR #540](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/540), head `0b948061f8df16ceb8588e19cd858a0fffea7ddc`, precisely 8 server/docs files.
- Over-budget encrypted-link traffic is dropped and counted/reported. The entire address is **not automatically banned**; operator ban-list enforcement remains.
- NAT regression ensures a second game from the same IPv4 address is still accepted after a noisy peer is throttled.
- Preserve deprecated `admin stats` key `bans: 0` for older read-only metrics clients; new `floods` remains canonical. This field is *not* an operator-ban count.
- Docker builder has an opt-in `verification-tests` target (12 server suites). Default `runtime` target remains unchanged.
- A bounded `curl` retry handles transient 504 errors downloading the **same** micromamba version and HTTPS URL.

## Evidence and promotion gates

1. All GitHub Actions unit tests and full Docker builder tests must pass. CI does not deploy or publish an image to a registry.
2. Use only an isolated shadNet with throwaway database and new throwaway keys for integration testing. Never connect the test container to the live volume or admin socket.
3. Prove team joins, shared-NAT concurrent game links, reconnect, operator bans, limits, authentication config, world storage, and clean shutdown/restart under 1.4.0 client behavior.
4. Compare incoming/outgoing UDP errors, `bad_tags`, `floods`, `link_load`, game latency, and world persistence against existing production before making an upgrade decision.
5. Production cutover requires an explicit maintenance window, exact current image digest, backup of current *new* data, a one-command rollback plan, and health checks. No CI/CD auto-deployment.

## Known production baseline (read-only)

- VPS: 4 vCPU, Docker host networking, `shadnet-shadnet-1`, restart policy `unless-stopped`.
- 20–23 players, roughly 605 worlds; link load around 0.09–0.12; 0 UDP kernel receive/send buffer errors during 60-second sample.
- 366 `bad_tags` (failed crypto tags) but **0** new `datagrams_dropped` and **0** new bans in that sample. This change addresses a possible failure mode, not a proven current incident.
- HTTPS password authentication currently works. Never rotate production `link_key.bin`, rewrite the database, change DNS, or restart Caddy for this branch.

## Next candidates from the wider GitHub ecosystem

- [Upstream PR #502](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/502): queued join greeting after game-link restart; draft and not yet fully gameplay-tested. **Do not merge blindly.**
- [Upstream PR #444](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/444): multi-enemy-owner load test. Useful for **test infrastructure**, not a production gameplay patch.
- [Upstream PR #435](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/435): source-revision provenance in Docker, further CI hardening candidate.
- Game-world progress overwrites, resurrected bosses/NPCs, and mod warnings must be traced to server-side state ownership before editing. Client/game-hook bugs stay upstream with their maintainers.

## User's operational preferences

No recurring server backups, no external backup target; user retains one local archive by choice. Do not add backup timers, backup retention jobs, Redis, PostgreSQL, or another systemd wrapper by default.

## Separation of concerns

This fork is for the current **compatible server**. Independent website migration and player-online API come after server hardening. Experimental BBHost/bbport client/launcher changes and a native PC port remain separate future projects.