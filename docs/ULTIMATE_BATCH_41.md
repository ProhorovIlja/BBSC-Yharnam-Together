# Ultimate B41: server-authenticated text chat admission foundation

**2026-11-09.** New user request: add **global text**, **current-team text** and **private /whisper** plus optional **proximity/team voice**. Tracked in [#95](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/95) and [#96](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/96). This patch deliberately addresses *only the server-side text-chat admission core*, not a visible or networked chat.

## Why this stage comes before the GUI

YT uses a reliable ordered Coop envelope for worlds and team events, while the server-side [TeamLobby](../server/coop/team_lobby.h) manages up-to-five hunters and user/team membership. A new broadcast packet without an authenticated audience gate would leak private/team messages after a team switch, between rooms, or across global-server accounts. Voice needs a *different* low-latency transport: it must not stall enemy/world-sync reliable queues.

## Real code delivered

- `server/coop/chat_policy.h`: header-only C++20 `BloodborneCoop::Comms::Gate` class. Derives the sender solely from an upstream **authenticated member ID** and the supplied **live authoritative roster**; no sender, team, server or source IP is accepted from a `Request`. Scoped audiences: **Global** (only this shard, and only when enabled), **Team** (same live team ID) and **Direct** (exact resolved account ID, never display name alone).
- Recipient opt-outs for global/team/direct, account-level block, sender `can_send`, private blocked/offline/unknown collapsed into the *same error* to avoid a block-list side channel. Sender does not get duplicated via fanout; positive verdict is a send acknowledgment. Repeated roster entries cannot duplicate delivery.
- Strict Unicode scalar UTF-8 validation, max **512 encoded bytes / 240 scalars**, no control, ANSI newline, invalid/overlong encodings or bidi override/isolate; rendering must still escape untrusted content. Shared per-account rate cap **six messages in ten seconds** across channels; bounded state for at most 4096 active account buckets; monotonic clock required. No network sockets, audio recording or credential handling.
- `server/tests/test_chat_policy.cpp`: C++ source tests for two separate teams, global vs group, private, membership changes, block/mute/opt-out, bad text, rate limit, roster duplicates, absent account.
- CMake/CTest registers `chat_policy`, and the dedicated GitHub Actions workflow builds the same header/test on **Linux GCC** and **Windows MSVC**.

## Integration blockers, in priority order

1. Wire actual `coop.proto` messages and server dispatch through `Gate` after **authenticated** link identification. The caller must provide a roster snapshot with current authoritative TeamLobby membership and never reset a per-account limiter on untrusted reconnect.
2. Resolve private names via per-server unambiguous account IDs, implement block/mute persistence and security policy, plus ack/retry and bounded queues. Never trust client-supplied team IDs, pre-cached room membership, or old host migration epochs.
3. Add true global **cross-shard** federation if global truly means all hunters on a region's server, with server identity, durable dedupe, backpressure and bounded fanout. The present gate routes only peers in its *supplied shard roster*. For dedicated servers, never carry messages/identities when switching the selected server.
4. Add UI and game overlay *after the end-to-end server route exists*: global/team/direct tabs, localized chat commands `/g`, `/team`, `/w`, `/r`, privacy settings, controller/keyboard bindings, appropriate notification settings.
5. Voice [#96](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/96) is independent: compare [Opus RFC 6716](https://www.rfc-editor.org/rfc/rfc6716), [Mumble positional audio](https://www.mumble.info/documentation/user/positional-audio/), [Mumble Link](https://www.mumble.info/documentation/developer/positional-audio/link-plugin/), and [libdatachannel](https://libdatachannel.org/) before selecting an encrypted real-time media transport. No claims of existing voice support.

## Branching and safety

Stacked on [B39 LAN/VPN adapter PR #94](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/94). **Existing parallel local-host population [#91](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/91) and regional compatibility [#92](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/92) branches have diverged.** Reconcile separately before final unified integration. Do not claim that using this B41 branch automatically includes #91/#92. Respect original upstream licenses and validate changes against other forks.

No changes to Fornex, public installer, private game files, character saves, game messages, existing runtime routing or network security configuration. **Draft/source test only: neither text nor voice chat is usable in the live game yet.**
