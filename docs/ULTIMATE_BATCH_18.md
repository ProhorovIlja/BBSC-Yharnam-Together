# Ultimate B18: bounded signup quota history without creating empty IP entries

**Scope:** production shadNet hosted admission on top of [B17 #49](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/49), retaining the complete B15 client/server Git merge and separate B16 Windows pipeline. This is a focused **server source change**, not a new client release or installer.

## Root cause confirmed by source inspection

Previously `Guard::MayMakeAccount(address, now_ms)` used `accounts[address]`, automatically inserting an empty list whenever the login/registration pipeline asked whether an unknown address **could** create an account. A cancelled, failed or abandoned registration still allocated one hash entry. Furthermore, the table of **genuinely created accounts** had no global retention cap and was cleaned only when the *same* address checked again. The server's `LinkServer::SignIn` invokes `MayMakeAccount` synchronously before `Made`, and calls `Unmade` on unsuccessful async sign-in. The B17 hello-bucket cap protects a different `hellos` map, so it did not fix this account map.

This is an observable unbounded-memory design issue in source, **not evidence of an exploited live server**.

## Corrected behavior

- A quota probe performs a non-inserting `QHash::find`. No account record exists until `Made` confirms the reservation. `Unmade` erases an address if the reservation was its final entry.
- `MaxAccountBuckets=100000` limits tracked distinct addresses with **recent actual account reservations**. Fresh quota histories must not be globally cleared by high-cardinality new-IP traffic; when full, a new address fails closed with the existing `accounts_refused` counter.
- On a saturated table, run at most one old-record cleanup sweep per 10 seconds. Remove only timestamps older than the **existing one-hour quota window** and drop a bucket only when its entire history is expired. Existing recent account histories remain intact and cannot be arbitrarily refreshed by another IP.
- An address already in the table can continue checking its own remaining quota while at global capacity. After its last old timestamp expires it may make a new reservation; this does not silently weaken the current `new_accounts_per_hour` limit. No bans, TLS, user ID, encrypted Link4 frames, five-hunter party cap, world saves or deployment behavior changed.
- **Tradeoff:** more than 100000 genuinely recently registering distinct source IPs can cause otherwise legitimate new source IPs to be temporarily refused. This is an intentional bounded-memory fail-closed guard, not a claim of optimal production sizing. It needs real traffic and IPv4 NAT monitoring.

## Repro and CI

The existing actual `server/tests/test_admission.cpp` gains two tests:
1. 100250 **non-committing** signup eligibility probes followed by 100000 real per-IP signup reservations, confirming empty probes consumed no slots, the 100001st real address is refused, spent per-IP quota remains spent, and capacity returns after one hour.
2. 100000 reservations with the last reservation refunded via `Unmade`, confirming a new address can take that immediately freed slot without evicting any existing recent quota.

These tests fail against the old unbounded/inserting behavior. A new narrow CI compiles and runs the **actual production** `admission.cpp` with Qt6/C++20, including inherited B17 100000-hello regression, plus real encrypted-link/watchdog checks. An exact six-file parent-diff and Git blob source pin prevents any unplanned changes.

**Non-claims:** no live Internet load test, real Bloodborne co-op gameplay, fully completed Windows B16 binary, CDN/launch installer, public release, Fornex restart or private savedata access. All remain mandatory release gates.
