# Ultimate B47: Unicode-aware Players browser and exact upstream UTF-8 scope

2026-11-10. Stacked on [B46 PR #105](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/105); follows [Hunters Online Issue #100](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/100).

**User-visible bug fixed in source:** the in-game Players browser previously used byte-wise `std::tolower()` on UTF-8 account display names, so query `охотник` could fail to match `ОХОТНИК` and mixed-case Cyrillic text. `bbport/gpu/bbcoop/roster_filter.h` now performs bounded, allocation-safe per-codepoint UTF-8 simple folding for ASCII, Latin-1, Greek and Cyrillic (including Ё/ё). The actual `bbport/gpu/shim/bbport_overlay.cpp::DrawPlayersPage` uses it for filter text and displayed names. Account-id de-duplication from B46 remains independent; case-insensitive name comparisons are **never** trusted for account identity or invitations.

**Verified behavior by code fixture:** Russian upper/lower, Ё, mixed English/Russian, accented Latin, Greek sigma, negative matches, truncated/malformed UTF-8, empty queries. Strict UTF-8 scalar decoding rejects invalid/incomplete sequences and copies malformed bytes instead of accidental out-of-bounds access. No locale, ICU or network dependency.

**Explicit limitation:** this is a safe **subset** of Unicode simple case folding, not full Unicode normalization/collation. German ß, Turkish I variants, combining marks, and all locale-specific equivalences can still differ. Filtering the bounded roster snapshot does not become full-server search, which remains the separate authenticated `BBCOOP_TEAM_SEARCH` query; it does not bypass privacy or expose non-listed accounts.

**Testing:** Windows/Linux Python contract verifies source integration into actual in-game browser, pure C++20 GCC/Clang compile/tests for Unicode and invalid input, and inherits the B46 actual Windows game-free native-client build gate. B47 does not pretend that source/portable compiler checks prove actual in-game localization. No game assets, saves, Fornex or release touched.

**External source watch:** original independent BBHost [PR #233](https://github.com/droogie/bbhost/pull/233) adds separate Windows UTF-8 process/path handling, already merged, but does not itself validate YT/BBPort's in-game roster Unicode filter. Evaluate BBHost display/path fixes independently rather than transplanting renderer code.
