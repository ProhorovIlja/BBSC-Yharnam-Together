# Ultimate B17: bounded admission hello memory without erasing active rate limits

**Date:** 2026-11-09. **Branch lineage:** B17 follows [B16 Draft PR #48](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/48), which follows the real B15 client/server merge [#47](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/47). This is one narrow **server-side protective source change**, not a full Windows or deployment rebuild.

## Source finding

The previous `Admission::Guard::AllowHello` implementation contained:

```cpp
if (hellos.size() > 100'000) {
    hellos.clear();
}
```

A large sequence of unique source addresses could therefore erase **every** in-use token bucket, including those of active addresses that had already consumed their allowed Hello burst. This undoes rate limits until they are spent again, potentially raising expensive sign-in / encrypted-handshake work. The test also demonstrates the source-memory hard cap is not respected at the exact threshold. This is a **verified source-level vulnerability**; no claim is made that external actors exploited a real server.

## Source fix

- `server/src/admission.h/.cpp` caps the address-to-hello-bucket map at **100,000** entries and preserves the buckets of active addresses. An unknown address is rejected with the normal `hellos_refused` counter when capacity is exhausted.
- On saturation, perform at most **one cleanup sweep per 10 seconds**. Retire buckets last used **at least two minutes** earlier, measured with the server's own monotonic milliseconds. This bounds memory and CPU per sweep without resetting legitimate clients' allowances. Old active players can continue refilling and using their existing buckets.
- No change to packet format, account authentication, encryption, peer identity, world save data, or operator ban policy. No player is automatically banned on traffic limits; original non-banning behavior is preserved.
- The hard cap can temporarily reject a **new** valid address if 100,000 different addresses were all active recently. This fail-closed state is a denial-of-service mitigation trade-off; monitor it and consider a better probabilistic/sharded implementation if measured peak legitimate unique IPs ever approaches capacity.

## Real C++ test

`server/tests/test_admission.cpp` adds `HelloFloodNeverResetsActiveBucketsOrGrowsUnbounded`. It spends the token burst for one address, floods **99,999 other unique source addresses**, verifies the next new source gets refused and the original exhausted address **remains refused**, then advances the clock two minutes and confirms old buckets are reclaimed and new clients can join. It also verifies the `hellos_refused` counter. This test would fail under the old `hellos.clear()` behavior.

The B17 GitHub Actions job compiles the real `server/src/admission.cpp` and real `test_admission.cpp` with **Qt6 C++20** on Ubuntu, executes the exact regression, and repeats the encrypted server-link and watchdog tests. It also runs inherited B12/B13 per-member join/Insight production C++ tests, checks 7 permitted B16→B17 files and immutable original server class source hashes. It does **not** trigger another full 110-minute Docker/Windows build just for this one line of server protection.

The B15 exact B14→B15 source gate is scoped to its original Draft PR #47; descendants have their own exact parent-to-head checks. This is not a removal of required test coverage.

## Still unverified

Real service load with 100,000 legitimate unique IPs, live network latency, IPv6 admission treatment, server monitoring, Windows client build, actual 2/3/5-player Bloodborne play and personal-world saves remain pending. Both B15 Docker integration and B16 Windows full compiler have separate runs; no result is implied by this document. No public releases, Fornex restart/SSH, credentials, private CUSA03173/DS3 assets or player saves are touched.
