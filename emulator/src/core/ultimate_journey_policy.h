// SPDX-FileCopyrightText: Copyright 2026 BBSC Ultimate contributors
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <cstdint>
#include <optional>

// A pure, fail-closed rule set. This does NOT invoke ESD talks, write game
// flags, change a save, spawn a boss or advance the cycle. A future game
// adapter must supply VERIFIED live values and act only after Confirm().
namespace Core::Bloodborne::UltimateJourney {

enum class Action { NewGamePlus, BossRematch };
enum class Place { Other, Doll, BossLamp, BrokenLamp };
enum class Decision {
    Allowed,
    Disabled,
    UnsupportedGame,
    UnknownCharacter,
    UnknownWorld,
    UnknownBoss,
    StaleSaveBackup,
    OnlineSessionBusy,
    WorldBusy,
    WrongPlace,
    NotEligible,
    NoSafeSaveBackup,
    ArenaUnavailable,
    ConfirmationMissing,
    ConfirmationStale,
};

struct Options {
    bool manual_new_game_plus = false;
    bool boss_rematches = false;
};

struct Snapshot {
    bool supported_game_version = false;
    std::uint64_t character_key = 0;
    std::uint64_t save_revision = 0;
    // The game adapter must increment this on each map/world load or reload,
    // even when a save operation has not taken place.
    std::uint64_t world_epoch = 0;
    // A known NG+0 is valid; unknown is never equivalent to NG+0.
    std::optional<std::uint32_t> cycle_index;
    // Specific boss and arena; 0 means no verified selection.
    std::uint32_t boss_id = 0;
    std::uint64_t arena_key = 0;
    Place place = Place::Other;
    bool ending_eligible = false;
    bool this_char_defeated_boss = false;
    bool rematch_arena_available = false;
    bool verified_backup = false;
    // A backup from an earlier save generation must not authorize a later one.
    std::uint64_t verified_backup_save_revision = 0;

    bool party_active = false;
    bool matchmaking = false;
    bool invasion = false;
    bool reconnecting = false;
    bool world_transition = false;
    bool save_in_progress = false;
};

// The rematch snapshot describes a particular boss selected by the current
// character, never a server-wide kill or another player's event flag.
// All multiplayer paths stay DENIED until isolated authoritative rematch
// sessions, rewards and rollback have their own proven implementation.
constexpr Decision Check(Action action, Options options, const Snapshot& s) {
    if (action == Action::NewGamePlus ? !options.manual_new_game_plus
                                      : !options.boss_rematches) {
        return Decision::Disabled;
    }
    if (!s.supported_game_version) {
        return Decision::UnsupportedGame;
    }
    if (s.character_key == 0 || s.save_revision == 0) {
        return Decision::UnknownCharacter;
    }
    if (s.world_epoch == 0 || !s.cycle_index) {
        return Decision::UnknownWorld;
    }
    if (s.party_active || s.matchmaking || s.invasion || s.reconnecting) {
        return Decision::OnlineSessionBusy;
    }
    if (s.world_transition || s.save_in_progress) {
        return Decision::WorldBusy;
    }
    if (action == Action::NewGamePlus) {
        if (s.place != Place::Doll) {
            return Decision::WrongPlace;
        }
        if (!s.ending_eligible) {
            return Decision::NotEligible;
        }
        if (!s.verified_backup) {
            return Decision::NoSafeSaveBackup;
        }
        if (s.verified_backup_save_revision != s.save_revision) {
            return Decision::StaleSaveBackup;
        }
    } else {
        if (s.place != Place::BossLamp && s.place != Place::BrokenLamp) {
            return Decision::WrongPlace;
        }
        if (s.boss_id == 0) {
            return Decision::UnknownBoss;
        }
        if (s.arena_key == 0) {
            return Decision::ArenaUnavailable;
        }
        if (!s.this_char_defeated_boss) {
            return Decision::NotEligible;
        }
        if (!s.rematch_arena_available) {
            return Decision::ArenaUnavailable;
        }
    }
    return Decision::Allowed;
}

// Two-phase UI intent: a single explicit confirmation, bound to exactly one
// character, save revision, action and location. A failed/stale confirmation
// always consumes the token. No implicit auto-NG+ or automatic rematch.
class Confirmation {
public:
    Decision Offer(Action action, Options options, const Snapshot& s) {
        pending.reset();
        const Decision decision = Check(action, options, s);
        if (decision == Decision::Allowed) {
            pending = Intent{action, s.character_key, s.save_revision, s.world_epoch,
                             *s.cycle_index, s.place, s.boss_id, s.arena_key};
        }
        return decision;
    }

    Decision Confirm(Action action, Options options, const Snapshot& current) {
        if (!pending) {
            return Decision::ConfirmationMissing;
        }
        const Intent intent = *pending;
        pending.reset();
        if (intent.action != action || intent.character_key != current.character_key ||
            intent.save_revision != current.save_revision ||
            intent.world_epoch != current.world_epoch ||
            !current.cycle_index || intent.cycle_index != *current.cycle_index ||
            intent.place != current.place || intent.boss_id != current.boss_id ||
            intent.arena_key != current.arena_key) {
            return Decision::ConfirmationStale;
        }
        return Check(action, options, current);
    }

    void Cancel() { pending.reset(); }

private:
    struct Intent {
        Action action;
        std::uint64_t character_key;
        std::uint64_t save_revision;
        std::uint64_t world_epoch;
        std::uint32_t cycle_index;
        Place place;
        std::uint32_t boss_id;
        std::uint64_t arena_key;
    };
    std::optional<Intent> pending;
};

} // namespace Core::Bloodborne::UltimateJourney
