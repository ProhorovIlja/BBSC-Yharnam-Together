# HTTPS connection budget for slow TLS handshakes

Source: [Awakenchan/LanternEngine #105](https://github.com/Awakenchan/LanternEngine/pull/105),
head `05c4b0c14b22efe4c2580825cbd55539bad1c870`, inspected open and unmerged. The upstream
report describes a one-second game connection budget expiring during a healthy TLS handshake.
The inspected body reports upstream gameplay success; that is not gameplay verification here.

The current `RunRealHttpRequest` has the same short-budget path, with pooled httplib clients.
`bbport/gpu/CMakeLists.txt` compiles this shared network module into bbnet as well as its use in
the emulator tree. Adapt the upstream ten-second connection floor **only for HTTPS**. Plain HTTP,
read/write timeouts, zero-means-default behavior and explicit larger connection budgets retain
their existing values. Each request/redirect reconfigures the pooled client. The floor is a
deadline, not a sleep or additional request. No TLS verification option changes in this patch.

The portable production header configures the same httplib setter API used by the request path.
Tests check 24 budget cases, rounding through maximum u32 microseconds, default read/write budgets
and reuse across HTTPS -> HTTP settings. Linux integration compiles the actual vendored httplib
client used by BBport with OpenSSL 3 and runs it against a loopback-only TLS server:

- A handshake delayed two seconds fails with `SSLConnection` under the old one-second budget.
- The production HTTPS policy returns HTTP 200 for the same delayed handshake with a trusted CA
  and hostname verification enabled.
- An untrusted self-signed certificate and a hostname mismatch remain rejected.
- A fast handshake succeeds well below the ten-second budget, confirming there is no added sleep.

Certificates and keys are generated in a temporary directory for this fixture, then removed.
No game/account data, credentials or external game server is involved. Exact elapsed times are
diagnostic observations, not internet latency benchmarks. CI runs the portable budget tests on
Windows/Linux/macOS; the real OpenSSL/TLS integration runs on Linux only.

Commands: `cmake -S tools/ultimate/http-tests -B build-http -DULTIMATE_LOCAL_TLS_TEST=ON`, build,
then CTest (OpenSSL 3 headers/library/CLI and Python required for the integration option).

This does not establish a full bbnet/client build, in-game login, Windows/macOS real TLS behavior,
production DNS/proxy/IPv6 behavior, cancellation timing or every redirect/pool lifecycle path.
The full local GPU/client build remains blocked by missing Vulkan SDK. A dead/slow HTTPS endpoint
may now spend up to ten seconds in the connection phase when the game requested less; other
existing timeout/cancellation behavior remains separate. The preceding HLE/GX guards and strict
prepared-native diagnostic are separate acceptance tracks.
