# Ultimate B44: usable team chat UI and server-sourced boss victory notices

2026-11-10. Stacked on Draft B43 PR #101: https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/101. Tracks Issue #100 and #95.

## Actual code

- Real existing B42 reliable protobuf team chat is now wired to game-side Receive and Send in emulator/src/core/bloodborne_server_world.cpp. TakeLobbyMessage accepts ChatEvent into a mutex-protected bounded 64-event queue, drained in batches; SendTeamChatText queues only scope=TEAM via the same Coop stream, with final sender/roster/UTF-8/flood validation still on the server.
- bbport/gpu/bbcoop.h and bbport/gpu/bbcoop/coop.cpp have a C bridge that supplies display-safe character names, typed chat events, acknowledgments, canonical boss flags, and team-only outgoing text. The user's raw identity/token/IP is not passed to the overlay.
- bbport/gpu/shim/bbport_overlay.cpp now includes a Chat / Чат button, a Team chat panel with Send by Enter/button, bounded 64-message local memory history, unread counter, rejected/pending statuses, a boss-event spoiler filter, and navigation to the Players button added in B43. This is the in-game team menu, not an always-visible gameplay overlay. No server-side persistent log of ordinary chat content was added.
- Server protocol ChatEvent has additive uint32 kind=6 and boss_flag=7: kind 0 is player text (old behavior), kind 1 is server-owned boss progression. Existing protocol number 8, earlier field tags and semantics are unchanged.
- server/coop/boss_victories.h contains 16 audited map boss-defeat flags. They are cross-checked against emulator/src/core/bloodborne_map.cpp::AreaBossFlags. Do not assert DLC/chalice completion coverage from this initial table.
- server/src/bloodborne_world.cpp::Service::TakeWorld only emits a victory on an accepted live host MapFlagOn delta for an audited flag on a map with a previously observed valid baseline. Initial map snapshots, rejoin/replay and switching maps with flags already enabled are not victory events. Per-world in-memory dedupe rejects repeated announcements. Recipients must be currently authenticated online links of the exact originating team and world; no outsiders/invaders or other teams. A generic localized client message appears; the player who defeated the boss is not named without consent.
- Actual C++ reliable CoopStream regression in server/tests/test_bloodborne_world.cpp: two authenticated teammates, unrelated third hunter in another team, guest attempting to claim victory, accepted host transition, repeat reports, rollback and first snapshot. Separate portable C++20 catalog test and Windows/Linux source tests accompany Docker Qt6/Protobuf world-service CTest.

## Trust and unresolved gates

The current server validates a client's accepted host map progression report, NOT independent simulation of a boss fight. A malicious patched host could still falsify the progression flag. Do not broadcast these notices globally or call them cryptographic proof of victory. Future upgrades: trusted encounter/HP chain, 2–5 real game clients, bosses' localized names, additional verified flags including DLC/chalice, opt-in public names, spoiler-safe cross-shard announcements and moderation.

Global and private text remain disabled pending exact account resolution, block/mute/privacy preferences, federation and abuse controls. Proximity/team voice independent. The new native ImGui/Win64 UI source is NOT compiled by the isolated server container; clean native Windows compiler and real in-game keyboard/controller tests remain mandatory for promotion. The older local raw-Link counter PR #91 and regional check PR #92 remain separate branches.

No changes to production Fornex, private game assets or player saves. PR Draft until integrated CI and game tests pass.
