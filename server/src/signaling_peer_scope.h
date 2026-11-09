// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// The TCP matching2 peer endpoint query may reveal addresses and start a P2P
// connection only to an actual member of the caller's active room. The server
// resolves the room by (matchingKey, roomId) before calling this helper, while
// holding roomsLock. Return copied data so no RoomMember pointer escapes it.
#include <cstdint>
#include <optional>
#include <QString>
#include "matching_types.h"

namespace SignalingPeerScope {

struct Peer {
    uint16_t memberId = 0;
    QString roomAddr;
    uint16_t roomPort = 0;
};

inline std::optional<Peer> Find(const Room& room, const QString& requesterNpid,
                                const QString& targetNpid) {
    if (requesterNpid.isEmpty() || targetNpid.isEmpty() || requesterNpid == targetNpid ||
        !room.findByNpid(requesterNpid)) {
        return std::nullopt;
    }
    const RoomMember* target = room.findByNpid(targetNpid);
    if (!target || target->memberId == 0)
        return std::nullopt;
    return Peer{target->memberId, target->addr, target->port};
}

} // namespace SignalingPeerScope
