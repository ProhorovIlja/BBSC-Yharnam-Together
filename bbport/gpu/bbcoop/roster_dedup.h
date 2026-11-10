// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Stable online roster rows from both current-team and selected-shard lists.
// The same authenticated account may be present in both sources. Prefer the
// team's row (it has current vital/level data) and never guess identity by name.
#include <cstring>
#include <vector>

namespace BbRoster {
template <typename Entry>
void AppendUniqueOnline(std::vector<const Entry*>& entries,
                        const Entry& player, int offline_state) {
    if (player.state == offline_state) return;
    if (player.id[0]) {
        for (const Entry* prior : entries) {
            if (prior->id[0] && std::strcmp(prior->id, player.id) == 0) return;
        }
    }
    // Empty account IDs are unknown: do NOT merge different players merely
    // because two characters chose the same display name.
    entries.push_back(&player);
}
} // namespace BbRoster
