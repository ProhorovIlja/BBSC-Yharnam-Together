# Playable issue intake — 2026-11-15

Snapshot against playable head `c2f6c24365a71cd57be8b1e8a090dcc90e0883a6` (draft #270), not the separate native-port stack.
GitHub issue search only, excluding pull requests. Closed items are retained to check for regressions.
This index records all returned issue titles and states, not a completed review of every issue body or comment.
For each candidate retain the source PR/commit, exact target evidence, reproduction, and validation status.
Do not close a report based solely on donor merge or CI compilation.

## First source-backed checks

| Area | Report | Finding / remaining evidence |
| --- | --- | --- |
| Launcher | Upstream #428 | Original stdout=None crash already guarded by console_text. This draft adds exact program-field matching, BOM decoding and rejection of missing output, with regression cases. Real localized Windows check still needed. |
| Client / GPU | Upstream #542 | Compared all added/context hunks across all 12 files of upstream #590; already present at pinned head, including vertex format and launcher error-log changes. Do not re-import. Direct Jgamrot #157/#209 lookups redirected; equivalence to both donor PRs and RTX hardware behavior remain unverified. |
| Client / co-op | Upstream #601; fork #164 | Matching Messenger Stump loop reports. No proven fix. Apply/remove/restart and rejoin on disposable saves; avoid globally clearing adornment or progression flags. |
| Client / co-op | Upstream #578 | Replace a chalice at the same altar; verify dungeon identity, door interaction and death respawn before and after rejoin. No fix asserted. |
| Client / input | Upstream #538 | Invite textbox accepts paste/backspace but not normal typing/Enter per report. Test focus and keyboard submission with the in-game menu; do not equate with launcher remapping tests. |
| Client + server | Upstream #532 | US path is recognized in this source and intentionally serves the shared document. HTTP 200 and identical US/EU bodies do not prove online login. Reproduce on CUSA00900 with exact Linux client and inspect discovery, login and hook readiness separately. |
| Client / save | Upstream #508; fork #224 | #269 retains per-player stock flags without destructive heuristic migration. Restart and already-affected saves still require separate evidence. |
| Server | #268 / #270 | Six-client loopback fix is a test-harness change; do not count as a production throughput improvement. |

Issue search also returned zero issues for NightAngellForks, oat018, edisnord, Tutuzaooo,
sousalucasc, nr-maker and nmoya Yharnam variants, kaoitp/yharnam-server-image and
SebValentine/Yharnam-Together-HuntersDream-Services-mod. Zero indexed issues does not
mean zero defects, no changes, or exhaustive coverage of all forks, refs and donor repositories.

## ProhorovIlja/BBSC-Yharnam-Together (132)

- [#3](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/3) — open — Server 1.4.0 hardening roadmap: compatibility, reconnect, world integrity, capacity and recovery
- [#9](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/9) — open — Ultimate Playable Edition: whole-ecosystem source audit, independent droogie BBHost vs bbport
- [#21](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/21) — open — P0 gameplay regression backlog: screenshot-reported invisible hunters, hot join, ActionEventInfo and unique save rewards
- [#22](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/22) — open — [P0][progression] Joining another player's world appears to overwrite individual world progression
- [#23](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/23) — open — [P0][co-op sync] Divergent enemy kills, NPCs, loot, boss and remote-hunter state
- [#24](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/24) — open — [P0][auth/SSL] Account registration and login: certificate not sent / invalid TLS
- [#25](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/25) — open — [P1][graphics/perf] Missing floors/materials; FPS decay over time and sluggish launcher movement
- [#26](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/26) — open — [P1][launcher/QoL] Leave-lobby button, safe offline diagnostics and mod anti-cheat false positives
- [#35](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/35) — open — [P0][guest rewards] Deferred boss/NPC awards must survive loading and never reach another save slot
- [#63](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/63) — open — [P0][NPC quests] Eileen/Henryk missing at Tomb of Oedon; NPC quest lines fail to advance or NPCs are invisible
- [#64](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/64) — open — [P1][new hunter / clinic] New character joining progressed host sees Celestial Emissary and Impostor Iosefka at tutorial start
- [#66](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/66) — open — [P1][external BBSC candidate] Vicar Amelia skull unusable for guest; personal sunset-to-night transition may stall
- [#69](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/69) — open — [P0][offline-only cheats] Restore v1.3.1 Save editor, legacy cheats and fair-play mode isolation
- [#70](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/70) — open — [P0][server mod compatibility] Compare only party members; classify cosmetic QoL vs online gameplay cheats
- [#71](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/71) — open — [P0][Cathedral Ward gate] Entrance door from Tomb of Oedon closed without interaction prompt
- [#72](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/72) — open — [P0][Hunter's Dream travel] Tombstones lack travel prompt after co-op teleport
- [#73](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/73) — open — [P0][chests/loot] Closed chests empty or no Open prompt until reconnect; per-character pickup isolation
- [#74](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/74) — open — [P1][friend requests] Declined invitation blocks resending with unclear and excessive cooldown
- [#75](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/75) — open — [P1][map collision] Hunter occasionally falls below world geometry; distinguish missing visual meshes/mods
- [#76](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/76) — open — [P1][historical source audit] Compare uploaded v1.3.1 portable/branches/patches to v1.4.0 Ultimate without binary transplant
- [#77](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/77) — open — [P1][launcher lifecycle] Very slow PLAY startup and slow termination after Alt+F4
- [#78](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/78) — open — [P1][in-game UI] Add Quit to Desktop to Bloodborne title screen with safe shutdown
- [#79](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/79) — open — [P0][NPC lifecycle] Henryk appears for a second after Tomb of Oedon warp, then disappears permanently
- [#80](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/80) — open — [P1][hybrid transport] Direct encrypted peer-to-peer game traffic with secure relay fallback and server-authoritative world
- [#84](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/84) — open — [P1][compatibility] Verify all nine retail Bloodborne CUSA regions, DLC entitlements and 1.09 seamless co-op
- [#85](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/85) — open — [P1][launcher observability] Hunters Online, accurate per-port health and SSL-safe network diagnostics
- [#86](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/86) — open — [P2][spectator] Host-controlled read-only co-op spectating, optional camera switching and rate-limited pings
- [#87](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/87) — open — [P2][launcher UX] Organize Ultimate settings into progressive sections, persistent search and safe presets
- [#89](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/89) — open — [P1][multi-server] Add/select dedicated Global server profiles with isolated sign-in, keys and Hunters Online
- [#93](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/93) — open — [P0][LAN/VPN Party] One-click Radmin/Tailscale/ZeroTier co-op discovery, no manual host IP or shadNet server
- [#95](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/95) — open — [Ultimate][Comms] Authenticated global / team / direct text chat with privacy and anti-spam
- [#96](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/96) — open — [Ultimate][Comms] Optional low-latency proximity voice chat, team voice, push-to-talk and privacy
- [#99](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/99) — open — [P2][Ultimate UX] Device-aware controller glyphs, native trophy notifications, and safe live graphics reload
- [#100](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/100) — open — [Ultimate][Social] Players browser, accurate Hunters Online and server-verified boss victory activity feed
- [#103](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/103) — open — [Ultimate][UX/PvP] Independent chat/map/player-info toggles, 18+ 4-stat build archetypes, invader aura and PvP quick match
- [#110](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/110) — open — [P1][Co-op] Doll Level Up quick cancel traps hunter kneeling; wait for both animation steps
- [#112](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/112) — open — [P1][NPC][Co-op] Doll Small Hair Ornament 'Give' option missing despite holding item
- [#114](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/114) — open — [P1][Co-op] Doll hit during teammate Level Up strands hunter kneeling; end local blessing safely
- [#116](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/116) — open — Ultimate: manual NG+ via Doll, persistent-safe boss rematches, mod compatibility and test matrix
- [#119](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/119) — open — Ultimate: expanded Discord Rich Presence, faction-private invader HUD and multi-invader DBNO rules
- [#122](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/122) — open — CI: reconcile legacy launcher suite with TEST branding, settings profiles and inaccessible temp folders
- [#130](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/130) — open — Ultimate cross-project intake: bloodborne_pc_windows_port runtime, P2P, graphics and launcher compatibility
- [#137](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/137) — open — [P0][phantom inventory] Persist guest-earned key items across exit/restart with verified save acknowledgement
- [#148](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/148) — closed — [P1][existing-character reload] Audit Hunt/Kin/Duel Bell icon, category and usability after loading a save
- [#161](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/161) — open — [P1][legacy CLS compatibility] Additional guests wait 180 seconds each
- [#162](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/162) — open — [P1][co-op] Guest remains suspended after a full boss wipe
- [#163](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/163) — open — [P1][runtime] Isolate Ebrietas encounter crash from post-respawn loading hang
- [#164](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/164) — open — [P1][co-op UI] Stump Messenger adornment animation repeats after application
- [#165](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/165) — open — [P1][solo compatibility] NPC summon prompts missing with YT enabled
- [#166](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/166) — open — [P1][startup/runtime] New hunter crashes when opening Iosefka's Clinic door
- [#167](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/167) — open — [P1][progression] Post-Rom route to The One Reborn stays closed after the cutscene
- [#168](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/168) — open — [P2][input] BBSC launch route loses keyboard/mouse input or mouse bindings
- [#169](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/169) — open — [Research B001] Turkish game and co-op language support
- [#170](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/170) — open — [Research B003] Discord ticket intake and inability to post bug reports
- [#171](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/171) — open — [Research B004] Parting Blank availability in the shop
- [#172](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/172) — open — [Research B005/B131] Configurable death, revive, spectator and respawn rules
- [#173](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/173) — open — [Research B006] Visible regional Discord tags
- [#174](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/174) — open — [Research B008] Native Linux and Steam Deck support
- [#175](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/175) — open — [Research B009] Development updates and release communication
- [#176](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/176) — open — [Research B012/B143] Discord update notifications, role pings and announcement permissions
- [#177](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/177) — open — [Research B013] Solo invasions and open sessions
- [#178](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/178) — open — [Research B014] Invader spawn distance to the host
- [#179](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/179) — open — [Research B015/B144] One-click installation, consistent branding and accurate setup documentation
- [#180](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/180) — open — [Research B017/B117] Voice-language controls and failing automatic language selection
- [#181](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/181) — open — [Research B018] Arabic letter shaping, right-to-left UI and game text
- [#182](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/182) — open — [Research B019] Separate language categories in Discord
- [#183](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/183) — open — [Research B020] BBR1 relay not started with bbhost disabled
- [#184](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/184) — open — [Research B021] Windows/Linux host-search and room-creation failures
- [#185](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/185) — open — [Research B023] Ultrawide crop, stretched menus and resolution mismatch
- [#186](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/186) — open — [Research B024] DLSS or FSR4 falls back to FSR3.1
- [#187](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/187) — open — [Research B028] Antivirus detection and WinError 225
- [#188](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/188) — open — [Research B029] Host echoes lost with no recoverable bloodstain
- [#189](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/189) — open — [Research B030/B049] Disabled bells after disconnect versus forced offline mode
- [#190](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/190) — open — [Research B035] Unlocked FPS causes stutter and physics problems
- [#191](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/191) — open — [Research B036] Invader stranded in the Hunter's Dream
- [#192](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/192) — open — [Research B041] Launch fails on empty JSON or malformed preparation data
- [#193](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/193) — open — [Research B042] Cathedral Ward / Gascoigne Dantelion2 panic on oversized lists
- [#194](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/194) — open — [Research B043] Save transfer between installs or versions crashes
- [#195](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/195) — open — [Research B044] Rune altar icons or unavailable gem workshop
- [#196](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/196) — open — [Research B046] Opening network settings crashes and prevents later launch
- [#197](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/197) — open — [Research B047] Infinite Insight from unanswered bells or Parting Blank
- [#198](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/198) — open — [Research B050] Invaders can open a host's doors
- [#199](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/199) — open — [Research B051] PLAY and OPEN LAUNCHER use different settings, saves or credentials
- [#200](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/200) — open — [Research B053] Green/purple/red screen or pixelated cutscene effects
- [#201](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/201) — open — [Research B054] Guest cannot finish the game or enter NG+
- [#202](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/202) — open — [Research B055] Windowed launch despite intended display mode
- [#203](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/203) — open — [Research B056] Crashes after 1.8.2 update or after hours of play
- [#204](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/204) — open — [Research B057] Crash on first attack, or when taking damage
- [#205](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/205) — open — [Research B058] Out-of-order flip IRQ assertion
- [#206](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/206) — open — [Research B061] Spectate/title overlay remains after a boss wipe
- [#207](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/207) — open — [Research B063] Chalice glyph search and community dungeons
- [#208](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/208) — open — [Research B064] Chalice co-op: void spawn, missing chest loot and echoes
- [#209](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/209) — open — [Research B065] Travel Together question cannot receive input
- [#210](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/210) — open — [Research B066] Elevator riders clip through the car
- [#211](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/211) — open — [Research B067] Post-Rom cutscene black screen
- [#212](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/212) — open — [Research B068] Bloodletter transformed L2 has no self-Frenzy
- [#213](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/213) — open — [Research B069] Yahar'gul mummy/NPC teleport black screen
- [#214](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/214) — open — [Research B070] Welcome announcement returns no information
- [#215](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/215) — open — [Research B072] Passworded guests join unrelated hosts
- [#216](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/216) — open — [Research B073] Host's old world rolls back after playing alone
- [#217](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/217) — open — [Research B075] Item-received popups repeat or guests receive random loot
- [#218](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/218) — open — [Research B076] Missing libc.prx, menu files and preparation-layer paths
- [#219](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/219) — open — [Research B080] FPS falls to 30 only after joining
- [#220](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/220) — open — [Research B081] Co-op difficulty and scaling do not match selected settings
- [#221](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/221) — open — [Research B083] Cloud saves tied to the co-op account
- [#222](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/222) — open — [Research B084] Individual lamp and shortcut recovery in a save editor
- [#223](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/223) — open — [Research B085] Boss placement, fog and physical obstruction after a retry
- [#224](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/224) — open — [Research B086] Shop purchases consume another player's stock
- [#225](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/225) — open — [Research B097] Silencing Blank appears to retain modded behaviour after uninstall
- [#226](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/226) — open — [Research B099] Guest cannot pass the Maria-clinic door without crashing
- [#227](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/227) — open — [Research B100] Guest pickups reappear after crash and rejoin
- [#228](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/228) — open — [Research B101] Guest-memory allocation failure, paging-file error and Windows error 1450
- [#229](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/229) — open — [Research B102] Audio missing or cuts out around co-op and launch transitions
- [#230](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/230) — open — [Research B103] Possible duplicated/reverberant audio
- [#231](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/231) — open — [Research B104] Temporary picture freezes while audio continues
- [#232](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/232) — open — [Research B105] Leave or Remove leaves a camera-only ghost in the old host world
- [#233](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/233) — open — [Research B108] Plain-text password in an older launcher coop.json: verify target scope
- [#234](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/234) — open — [Research B109] Shared installer identity and wrong update channel replace another installation
- [#235](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/235) — open — [Research B113] Shooters change into orange-coated sabre enemies with invisible legs
- [#236](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/236) — open — [Research B118] Brazilian Portuguese selection does not change to the requested localization
- [#237](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/237) — open — [Research B121] Vileblood Register missing while initial messenger weapons can be taken twice
- [#238](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/238) — open — [Research B122] Second game instance cannot launch from the same game folder
- [#239](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/239) — open — [Research B124] Legacy relay: cross-session broadcast, CPU and bandwidth amplification
- [#240](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/240) — open — [Research B126] Public-server deployment mode: audit historical Hosted=false configuration
- [#241](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/241) — open — [Research B129] Public websites and game services are unreachable from some regions
- [#242](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/242) — open — [Research B130] Unicode game/profile paths break Windows setup and launch scripts
- [#243](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/243) — open — [Research B132] Five-player co-op and separate team-duel, FFA and arena proposals
- [#244](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/244) — open — [Research B135] Dedicated jump on L3 or a Circle/L3 jump option
- [#245](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/245) — open — [Research B136] More Options at Lamp: upgrade, storage, shops, gems, runes and level-up
- [#246](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/246) — open — [Research B137] Respec and full appearance editor from the Dream or a lamp
- [#247](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/247) — open — [Research B142] Repeated Alt+Tab precedes a game crash
- [#248](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/248) — open — [Research B146] Enable static red-zone protection by default for Bloodborne setup

## Amanises-Yharnam-Together/BBSC-Yharnam-Together (7)

- [#428](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/428) — closed — [Bug] Launcher hangs at PLAY / Start server due to firewall_ready() AttributeError on Windows
- [#508](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/508) — open — [Bug?] Messenger purchases exhaust other party members stock
- [#532](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/532) — open — Failed to resolve Bloodborne server status
- [#538](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/538) — open — Coop menu not working, cannot type text or invite friends!
- [#542](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/542) — open — NVIDIA "GPU device lost (WriteInvalid at 0x0)": please merge upstream fixes #157 and #209
- [#578](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/578) — open — Chalice dungeon mixing
- [#601](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/issues/601) — open — Stuck in repeating animation in Hunter's Dream after giving Messenger's Stump a hat
