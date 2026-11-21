// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/bloodborne_reward_safety.h"

#include <cassert>
#include <iterator>
#include <string>

using namespace Core::Bloodborne::RewardSafety;
using namespace std::chrono_literals;

int main(int argc, char** argv) {
    assert(argc == 2);
    const Owner original{2, 1}, other_slot{3, 1}, other_character{2, 2}, unknown{-1, 1};
    ReturnAttempts attempts;
    assert(attempts.Begin(101));
    assert(!attempts.Begin(101));
    assert(attempts.Begin(201)); // another good can be earned while the first is ambiguous
    assert(!attempts.Begin(101));
    attempts.Reset();
    assert(attempts.Begin(101));
    const Time now{};
    std::vector<Pending<int>> lots{{101, now, original}, {102, now + 2s, original},
                                   {201, now, other_slot}, {301, now, other_character}};
    assert(HasDue(lots, original, now));
    assert(!HasDue(lots, original, now - 1s));
    assert(!HasDue(lots, unknown, now));
    assert(TakeDue(lots, unknown, now).empty() && lots.size() == 4);
    assert(HasDue(lots, original, now + 30s) && lots.size() == 4);
    assert(TakeDue(lots, original, now) == std::vector<int>{101});
    assert(lots.size() == 1);
    assert(TakeDue(lots, original, now).empty());
    assert(TakeDue(lots, original, now + 2s) == std::vector<int>{102});
    assert(TakeDue(lots, original, now + 30s).empty());

    const auto path = std::filesystem::path(argv[1]) / "phantom_keys";
    auto temp = path;
    temp += ".tmp";
    const auto read = [&] {
        std::ifstream in(path, std::ios::binary);
        return std::string(std::istreambuf_iterator<char>(in), {});
    };
    assert(WriteLedger(path, "first"));
    assert(read() == "first" && !std::filesystem::exists(temp));
    assert(WriteLedger(path, "second"));
    assert(read() == "second" && !std::filesystem::exists(temp));
    const auto unrelated = path.parent_path() / "keep_me";
    std::ofstream(unrelated, std::ios::binary) << "unrelated";
    std::error_code link_error;
    std::filesystem::create_hard_link(unrelated, temp, link_error);
    if (!link_error) {
        assert(!WriteLedger(path, "must not truncate the link target"));
        assert(read() == "second" && ReadLedger(unrelated) == "unrelated");
        assert(std::filesystem::equivalent(unrelated, temp));
        assert(std::filesystem::remove(temp));
    }
    std::ofstream(temp, std::ios::binary) << "stale";
    assert(!WriteLedger(path, "must not consume stale staging"));
    assert(!WriteLedger(path, {})); // Clearing must not bypass the same staging guard.
    assert(ReadLedger(temp) == "stale" && read() == "second");
    assert(std::filesystem::remove(temp));
    std::filesystem::create_symlink(unrelated, temp, link_error);
    if (!link_error) {
        assert(!WriteLedger(path, "must not follow temporary symlink"));
        assert(ReadLedger(unrelated) == "unrelated" && read() == "second");
        assert(std::filesystem::remove(temp));
    }
    assert(std::filesystem::remove(unrelated));
    assert(std::filesystem::create_directory(temp));
    assert(!WriteLedger(path, "must not replace second"));
    assert(read() == "second");
    assert(std::filesystem::remove(temp));
    assert(WriteLedger(path, "retry"));
    assert(read() == "retry");
    assert(WriteLedger(path, {}) && !std::filesystem::exists(path));
    assert(std::filesystem::create_directory(temp));
    std::ofstream(temp / "ledger") << "interrupted";
    assert(!WriteLedger(path, {}));
    assert(ReadLedger(temp / "ledger") == "interrupted");
    assert(!ReadLiveLedger(path));
    std::ofstream(path, std::ios::binary) << "committed";
    assert(!ReadLiveLedger(path));
    assert(ReadLedger(path) == "committed");
    assert(!LedgerStagingClear(path));
    assert(std::filesystem::remove(path));
    assert(!std::filesystem::exists(path));
    assert(std::filesystem::remove(temp / "ledger") && std::filesystem::remove(temp));
    assert(WriteLedger(path, {}));
    assert(LedgerStagingClear(path));
    assert(ReadLiveLedger(path) == std::string{});
    const std::string limit(MaxLedgerBytes, 'x');
    assert(WriteLedger(path, limit) && ReadLedger(path) == limit);
    assert(!WriteLedger(path, limit + 'x') && ReadLedger(path) == limit);
    std::ofstream(path, std::ios::binary | std::ios::app).put('x');
    assert(!ReadLedger(path));
    assert(std::filesystem::file_size(path) == MaxLedgerBytes + 1);
    assert(std::filesystem::remove(path));
    assert(std::filesystem::create_directory(path));
    assert(!ReadLedger(path));
}
