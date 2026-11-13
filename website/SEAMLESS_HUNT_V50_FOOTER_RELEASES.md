# V50 — Download footer and release-aware guides

[Private staging kit](https://drive.google.com/file/d/1gjOgFgGjk08kLP2yl75216Tz2CIn1sOG/view). Stage with `python3 stage_v50.py SOURCE NEW_DESTINATION` from V49. No deployment or service changes.

Download adds the GitHub icon and label to the social row alongside YouTube, Discord and X; Source code and Report a bug remain. The duplicate V49 release panel on Download is removed while preserving the four coordinated download and checksum links. Home and guide pages reuse the V49 release feed. The dated install intro is replaced only where its reviewed phrase matches; v1.5.0 behavior/history references, screenshots, unrelated product versions and CLS links are left alone. The tag is metadata, not a claim that screenshots and instructions were validated for that release.

Local V49-export staging and scoped copy fixture passed. Isolated Chromium DOM checks verified the footer, mock new release propagation on six pages, paired assets, and stale-feed fallback. VPS stage and production remain unmodified.
