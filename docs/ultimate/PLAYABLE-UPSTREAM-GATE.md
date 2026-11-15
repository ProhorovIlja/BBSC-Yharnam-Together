# Playable integration: upstream intake and game gate

The latest published upstream release observed was v1.5.0. Upstream has merged v1.5.1
notes (#600); notes are not a published installer. Do not compare against a presumed
1.5.1 release. Pin the exact upstream build and this candidate when recording results.

Already ancestors of the candidate before this intake: YT #589 personal shop stock,
#590 NVIDIA device-loss fix, #591 invisible teammate after load, #593 crash fixes and
GOTY 1.09 detection from Supermedo, #596 join greeting on link restart, #597 sign-in
status, and #598 Linux build. Do not import them again.

YT #592: the candidate already has the personal-world and lamp behavior in separately
hardened code, so do not replace those runtime files. Port only the missing autoplay
verb and game-rig scenarios. YT #599: the corrected pickup sequence was already present
in suites.py; port the missing regression. Upstream reported a separate intermittent
enemy takeover stall; a rig fix is not a fix for that stall.

Run the same two-player save clones on both builds. Use guest-own-lamps,
guest-new-world-own-progress, key-items-after-quit, then crashes/leave and
owner-crash-fight. Compare saved flags, item outcomes and reconnect logs after restart;
use separate installs, saves and local servers. No personal save or public server.
No new NPC/boss features, progression mode or EBOOT-free work in this gate.
