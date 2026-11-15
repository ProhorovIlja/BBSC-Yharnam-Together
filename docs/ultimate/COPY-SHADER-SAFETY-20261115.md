# Bounded copy-shader HLE adaptation

The current HLE fallback asserted on foreign buffer shapes, read the control table through raw
guest pointers, calculated offsets and `end + 1` in 32 bits, and dirtied the original unbounded
destination ranges even if no valid copy should run. This change rejects foreign shapes, bounds
each record by 64 lanes and both descriptors, reads mapped control records through the existing
backing-view API, checks mapped batch ranges and marks only copies actually submitted as dirty.
Zero-byte copies are omitted; scratch vectors are thread-local. Warning counts are atomic and
limited to the first eight occurrences per reason and subsequent powers of two.

Source: [Supermedo/bloodborne_pc #155](https://github.com/Supermedo/bloodborne_pc/pull/155),
head `b946f03de8f63ce2b063c68d043db304182126f5`, by kanggu12, GPL-2.0-or-later.
The PR was closed without a merge when inspected; this does not establish whether equivalent
changes reached another upstream branch. The shape/range helper and original regression cases
come from that revision. The local integration retains the current buffer-cache signatures,
the existing MultiCopy path and translated-shader selection. It adds backing-view reads for the
local protected guest-memory model, overflow checks, bounded dirty marking and independent tests.

This is a partial adaptation of #155: its frame-generation release, command-buffer recovery,
queue diagnostics and pipeline-permutation changes are not imported here. This branch normally
selects the translated shader with guest-in-place memory; blanket reuse of one HLE permutation
would change that path. The HLE guard does not validate that translated path or protect every
compute dispatch.

Validation:
- Upstream shape/crash descriptors, overflow and range edge cases are retained.
- 104,096 deterministic cases compare the production range helper with an independent 64-lane
  bounds oracle, including maximum 32-bit values.
- Nine scenarios execute the **extracted production HLE function** against recording memory and
  renderer interfaces: valid copies, foreign formats, unmapped controls/destinations, empty ranges,
  descriptor-limited groups, zero groups, address overflow and a valid batch after an unmapped one.
  They check backing reads, submitted ranges and dirty marks. The fixture is regenerated from the
  actual source during each build; it is not a copied algorithm.
- `cmake -S tools/ultimate/copy-tests -B build-copy`, build, then CTest. CI covers Linux, Windows and
  macOS, including ARM64 macOS because these tests are portable CPU code.

The fixture uses test doubles for Vulkan/cache/mapping and does not validate actual driver calls,
GPU synchronization, concurrent unmapping or the backing view's freshness. Full GPU configuration
locally is blocked by missing Vulkan headers/library. There is no GPU/gameplay/crash-rate or FPS
acceptance for this adaptation. Existing performance numbers in the source predate this change.

Other intake this increment inspected recent PR lists in ayozetr/bloodborne_linux,
Supermedo/bloodborne_pc, Mrsuss60/bloodborne_pc_windows_port, visy/bloodborne_pc_windows_port,
CLSAMG22/BBSC and Jgamrot/yharnam-pc. In particular, CLSAMG22 #47/#48 and Jgamrot #173 were inspected
but not imported. This is bounded source intake, not a claim to have audited all GitHub or the web.
