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
    assert(std::filesystem::create_directory(temp));
    assert(!WriteLedger(path, "must not replace second"));
    assert(read() == "second");
    assert(std::filesystem::remove(temp));
    assert(WriteLedger(path, "retry"));
    assert(read() == "retry");
    assert(WriteLedger(path, {}) && !std::filesystem::exists(path));
    assert(WriteLedger(path, {}));
    assert(ReadLedger(path) == std::string{});
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
