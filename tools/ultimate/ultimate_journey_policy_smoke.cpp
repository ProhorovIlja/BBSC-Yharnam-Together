// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/ultimate_journey_policy.h"
#include <cassert>

using namespace Core::Bloodborne::UltimateJourney;

constexpr Options kAllOn{true, true};

Snapshot ReadyNG() {
    Snapshot s;
    s.supported_game_version = true;
    s.character_key = 97;
    s.save_revision = 8;
    s.place = Place::Doll;
    s.ending_eligible = true;
    s.verified_backup = true;
    return s;
}

Snapshot ReadyRematch() {
    auto s = ReadyNG();
    s.place = Place::BossLamp;
    s.this_char_defeated_boss = true;
    s.rematch_arena_available = true;
    return s;
}

int main() {
    auto ng = ReadyNG();
    auto rematch = ReadyRematch();
    assert(Check(Action::NewGamePlus, {}, ng) == Decision::Disabled);
    assert(Check(Action::BossRematch, {}, rematch) == Decision::Disabled);
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::Allowed);
    assert(Check(Action::BossRematch, kAllOn, rematch) == Decision::Allowed);

    ng.supported_game_version = false;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::UnsupportedGame);
    ng = ReadyNG();
    ng.character_key = 0;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::UnknownCharacter);
    ng = ReadyNG();
    ng.save_revision = 0;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::UnknownCharacter);
    ng = ReadyNG();
    ng.party_active = true;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::OnlineSessionBusy);
    ng = ReadyNG();
    ng.matchmaking = true;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::OnlineSessionBusy);
    ng = ReadyNG();
    ng.invasion = true;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::OnlineSessionBusy);
    ng = ReadyNG();
    ng.reconnecting = true;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::OnlineSessionBusy);
    ng = ReadyNG();
    ng.world_transition = true;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::WorldBusy);
    ng = ReadyNG();
    ng.save_in_progress = true;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::WorldBusy);
    ng = ReadyNG();
    ng.place = Place::Other;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::WrongPlace);
    ng = ReadyNG();
    ng.ending_eligible = false;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::NotEligible);
    ng = ReadyNG();
    ng.verified_backup = false;
    assert(Check(Action::NewGamePlus, kAllOn, ng) == Decision::NoSafeSaveBackup);

    rematch = ReadyRematch();
    rematch.this_char_defeated_boss = false;
    assert(Check(Action::BossRematch, kAllOn, rematch) == Decision::NotEligible);
    rematch = ReadyRematch();
    rematch.rematch_arena_available = false;
    assert(Check(Action::BossRematch, kAllOn, rematch) == Decision::ArenaUnavailable);
    rematch = ReadyRematch();
    rematch.place = Place::Other;
    assert(Check(Action::BossRematch, kAllOn, rematch) == Decision::WrongPlace);
    rematch = ReadyRematch();
    rematch.place = Place::BrokenLamp;
    assert(Check(Action::BossRematch, kAllOn, rematch) == Decision::Allowed);
    rematch = ReadyRematch();
    rematch.party_active = true;
    assert(Check(Action::BossRematch, kAllOn, rematch) == Decision::OnlineSessionBusy);

    Confirmation c;
    ng = ReadyNG();
    assert(c.Confirm(Action::NewGamePlus, kAllOn, ng) == Decision::ConfirmationMissing);
    assert(c.Offer(Action::NewGamePlus, kAllOn, ng) == Decision::Allowed);
    ng.save_revision += 1;
    assert(c.Confirm(Action::NewGamePlus, kAllOn, ng) == Decision::ConfirmationStale);
    assert(c.Confirm(Action::NewGamePlus, kAllOn, ng) == Decision::ConfirmationMissing);
    ng = ReadyNG();
    assert(c.Offer(Action::NewGamePlus, kAllOn, ng) == Decision::Allowed);
    assert(c.Confirm(Action::BossRematch, kAllOn, ng) == Decision::ConfirmationStale);
    assert(c.Offer(Action::NewGamePlus, kAllOn, ng) == Decision::Allowed);
    ng.party_active = true;
    assert(c.Confirm(Action::NewGamePlus, kAllOn, ng) == Decision::OnlineSessionBusy);
    ng = ReadyNG();
    assert(c.Offer(Action::NewGamePlus, kAllOn, ng) == Decision::Allowed);
    c.Cancel();
    assert(c.Confirm(Action::NewGamePlus, kAllOn, ng) == Decision::ConfirmationMissing);
    assert(c.Offer(Action::NewGamePlus, kAllOn, ng) == Decision::Allowed);
    assert(c.Confirm(Action::NewGamePlus, kAllOn, ng) == Decision::Allowed);
    assert(c.Confirm(Action::NewGamePlus, kAllOn, ng) == Decision::ConfirmationMissing);
    assert(c.Offer(Action::BossRematch, kAllOn, ReadyRematch()) == Decision::Allowed);
    auto stale = ReadyRematch();
    stale.character_key += 1;
    assert(c.Confirm(Action::BossRematch, kAllOn, stale) == Decision::ConfirmationStale);
}
