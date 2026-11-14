# Ultimate: launcher sidebar, window movement, and acceptance gates

Status: two source changes on the experimental branch; no packaged build or production changes.

## Implemented in the existing launcher

- `a19cf2d81d8adc5f2ee4ed341ea68003509ba1d2`: one gold status line between the divider and Home, based on the supplied v1.5.0 sidebar. Reads the same public area snapshot used for the website count. One worker at a time, HTTPS only at the expected URL, bounded JSON, freshness validation, zero distinct from unavailable. The text explicitly identifies Seamless Hunt and does not pretend to count a selected custom or local server. No sign-in, no credential transmission, and no blocking HTTP on the Tk thread. Success interval 30 seconds; failure interval 60 seconds; minimized/withdrawn skips starting a request.
- `fa04eb94a5c54559abbabdd0275e734f8388f0f2`: custom Windows chrome moves through GetCursorPos/GetWindowRect and SetWindowPos, using the current cursor and native coordinates; does not resize, activate or change z-order. Retains Tk fallback. This targets geometry lag and signed desktop coordinates, not proof that all UI lag is gone. Verify on Windows at 100/150/200% DPI, secondary monitor left/up of primary, over heavy Home/Settings screens, with and without motion, and while resizing/maximizing independently.

Files: `bbport/launcher/bbport_launcher_win.py`. Both commits use the same experimental branch as the hybrid model. Do not promote automatically. This run did not launch the Windows GUI or ship a binary.

## Timing and patch compatibility

The fork already has uncapped/limited presentation presets and per-subsystem timing patches in `bbport/scripts/patches.py`: cloth, foliage, jump drag, and 1/60 s effects for applicable presets. Those do not establish a general fixed simulation clock. Inventory every actual consumer before changing it: simulation and collisions, gameplay animation/event notifies, Havok, input capture, guest scripts, camera, particles and presentation. Preserve the reference behavior, even where the original game requires calibrated 30 FPS semantics. Target a 60 Hz simulation with separate render pacing and interpolation; keep frame generation out of simulation and report generated and real frames separately. A bounded catch-up policy is required; never silently drop authoritative transitions. No extra binary patch enabled in this batch.

Compare `droogie/bbhost` frame manager (variable real-time steps, not a fixed-60 implementation), existing YT timing/overlap guards and high-FPS fixes. Inventory supplied patches by game build, expected original bytes, changed ranges, semantic feature and dependencies. Reject both byte overlap and double ownership of a timing subsystem; inspect license before import. The stock 1.09 fixture stays local, not in GitHub. Benchmark same scene and inputs at 30/60/90/120/uncapped render, with forced stalls and CPU/GPU-bound runs: movement distances, dodges and hit windows, gravity, parry windows, boss transitions, scripts and co-op consistency. Compare median/p95/p99 actual frame time, stutters, RAM/VRAM peaks, CPU/GPU time and bytes per player; report Windows and Linux separately. Validate before promoting unlocked FPS defaults.

## Gameplay, public sessions and releases

- Exact label: **Quit to Desktop**. Use normal save flush and co-op teardown; test while saving, in team, in invasion, and on gamepad. No hard kill.
- **Hide invaders' red glow (your screen only)**: local render toggle. Do not change team identity, damage, targeting or other players' display; default OFF.
- Invasion search for one or two: only explicitly eligible, open rooms with host opt-in and enough invader slots, not ordinary free co-op seats. Server atomically reserves all requested slots or none; bind reservation to roster, room epoch and TTL. Revalidate on admit and release on timeout/cancel/disconnect. Test concurrent requests for the final slots, permission change, host travel, partial join and faction separation. Use Dark Souls as a behavior reference, not a binary transplant.
- Hybrid stays relay-authoritative for admissions, world state and rewards; only proven transient streams become direct-eligible. Benchmark loss, jitter, ordering, fallback, server CPU/egress and client frame time. Existing P0 save/reward issues #22 and #35 remain release gates.
- Keep update origin unchanged until a verified release exists. Future Ultimate releases must use `ProhorovIlja/BBSC-Yharnam-Together`, explicit preview/stable channel, trusted manifest/artifact verification, staged replacement and rollback. Never overwrite user files/saves. Do not direct stable clients to experimental branches or releases.

No deployment, public account migration, native simulation change, invasion implementation, or updater switch in this batch.
