// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// B25: a matching context's initialized flag is *not* room ownership.
// Matching2 ContextStop and disconnect must retire an occupied room even when
// the context was already marked stopped. Create/Join/Start must never replace
// a live room identifier without leaving the previous room first.
#include <cstdint>
#include "matching_types.h"

namespace MatchingLifecycleGuard {

inline bool MayEnterRoom(const MatchingSessionState& state) {
    return state.roomId == 0;
}

inline uint64_t RoomRequiringCleanup(const MatchingSessionState& state) {
    return state.roomId;
}

} // namespace MatchingLifecycleGuard
