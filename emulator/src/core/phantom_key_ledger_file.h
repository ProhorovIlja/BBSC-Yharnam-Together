// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// B68 offline-only append-only key-item debt revision staging. Never called by
// live game/save hooks before identity and grant-acknowledgement wiring exists.
// This protects against ordinary process errors, NOT OS power loss (no
// portable directory fsync), and is not a multi-file atomic save transaction.

#include <algorithm>
#include <array>
#include <charconv>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <istream>
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>

namespace BloodborneCoop::PhantomKeyLedgerFile {

inline constexpr std::uint64_t MaxRevisions = 32768;
inline constexpr std::size_t MaxRecordBytes = 70 * 1024;

// An on-disk size check is not a read limit: another process could append
// data after file_size() and before an unbounded iterator-based stream read.
// Accept exactly the checked byte count, reject both truncation and growth,
// and NEVER allocate beyond MaxRecordBytes (even for a changing file).
namespace detail {
inline std::optional<std::string> ReadExactRecord(std::istream& in, std::size_t expected) {
    if (expected > MaxRecordBytes || !in) return std::nullopt;
    std::string data(expected, '\0');
    const auto bytes = static_cast<std::streamsize>(expected);
    in.read(data.data(), bytes);
    if (in.gcount() != bytes || in.bad()) return std::nullopt;
    if (in.peek() != std::char_traits<char>::eof() || in.bad()) return std::nullopt;
    return data;
}
} // namespace detail

struct Revision {
    unsigned slot = 0;
    std::string character_fingerprint; // 32 hex ASCII bytes, not a player name
    std::uint64_t sequence = 0;
    std::string debt; // canonical EncodeOwedKeyItems or tombstone ""
    bool operator==(const Revision&) const = default;
};

// Canonical debt list, same contract as the game-side strict parser.
// An empty payload is an explicit committed tombstone: NEVER infer one from
// a missing/truncated file. No bells, duplicate items, extra whitespace or
// malformed lines may be persisted.
inline bool CanonicalDebt(std::string_view payload) {
    if (payload.size() > 64 * 1024) return false;
    std::array<std::uint64_t, 256> encountered{};
    std::size_t count = 0;
    while (!payload.empty()) {
        const auto newline = payload.find('\n');
        if (newline == payload.npos || count == encountered.size()) return false;
        const auto row = payload.substr(0, newline);
        payload.remove_prefix(newline + 1);
        const auto first_space = row.find(' ');
        if (first_space == row.npos) return false;
        const auto second_space = row.find(' ', first_space + 1);
        if (second_space == row.npos) return false;
        const auto fields = std::array{
            row.substr(0, first_space),
            row.substr(first_space + 1, second_space - first_space - 1),
            row.substr(second_space + 1)};
        std::array<std::uint64_t, 3> nums{};
        for (std::size_t i = 0; i < 3; ++i) {
            if (fields[i].empty()) return false;
            const auto [ptr, err] = std::from_chars(fields[i].data(),
                                                     fields[i].data() + fields[i].size(), nums[i]);
            if (err != std::errc{} || ptr != fields[i].data() + fields[i].size() ||
                std::to_string(nums[i]) != fields[i]) return false;
        }
        if (nums[0] == 0 || nums[0] > UINT32_MAX ||
            nums[1] == 0 || nums[1] > INT32_MAX ||
            nums[2] > INT32_MAX || nums[2] < nums[1] ||
            nums[0] == 200 || nums[0] == 205 || nums[0] == 225 || nums[0] == 4312 ||
            std::find(encountered.begin(), encountered.begin() + count,
                      nums[0]) != encountered.begin() + count) return false;
        encountered[count++] = nums[0];
    }
    return true;
}

inline bool Valid(const Revision& r) {
    // Match the retail game's ten supported userdata0000..userdata0009
    // slots. The old offline-only contract accepted 10..63 despite the
    // live item owner gate rejecting them; never persist invalid owners.
    if (r.slot >= 10 || r.sequence == 0 || r.sequence > MaxRevisions ||
        r.character_fingerprint.size() != 32 ||
        !CanonicalDebt(r.debt)) return false;
    return std::all_of(r.character_fingerprint.begin(), r.character_fingerprint.end(),
                       [](unsigned char c) {
                           return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
                       });
}

inline std::uint64_t Checksum(std::string_view str) {
    std::uint64_t result = 14695981039346656037ull;
    for (unsigned char ch : str) {
        result ^= ch;
        result *= 1099511628211ull;
    }
    return result;
}

inline std::string Name(const Revision& r) {
    return "slot" + std::to_string(r.slot) + "-" + r.character_fingerprint +
           "-r" + std::to_string(r.sequence);
}

inline std::string Encode(const Revision& r) {
    return "BLOODBORNE_OWED_V1\n" + std::to_string(r.slot) + "\n" +
           r.character_fingerprint + "\n" + std::to_string(r.sequence) + "\n" +
           std::to_string(r.debt.size()) + "\n" +
           std::to_string(Checksum(r.debt)) + "\n" + r.debt;
}

inline std::optional<std::uint64_t> UInt(std::string_view str) {
    if (str.empty()) return std::nullopt;
    std::uint64_t value = 0;
    auto [it, error] = std::from_chars(str.data(), str.data() + str.size(), value);
    if (error != std::errc{} || it != str.data() + str.size()) return std::nullopt;
    return value;
}

inline std::optional<Revision> Decode(std::string_view text) {
    if (text.size() > MaxRecordBytes) return std::nullopt;
    const auto line = [&text]() -> std::optional<std::string_view> {
        const auto i = text.find('\n');
        if (i == text.npos) return std::nullopt;
        const auto first = text.substr(0, i);
        text.remove_prefix(i + 1);
        return first;
    };
    if (line() != "BLOODBORNE_OWED_V1") return std::nullopt;
    const auto slot = line();
    const auto fingerprint = line();
    const auto seq = line();
    const auto length = line();
    const auto checksum = line();
    if (!slot || !fingerprint || !seq || !length || !checksum) return std::nullopt;
    const auto nslot = UInt(*slot), nseq = UInt(*seq);
    const auto nlen = UInt(*length), nhash = UInt(*checksum);
    if (!nslot || !nseq || !nlen || !nhash || *nlen != text.size() ||
        *nslot >= 10) return std::nullopt;
    Revision r{static_cast<unsigned>(*nslot), std::string(*fingerprint),
               *nseq, std::string(text)};
    if (!Valid(r) || Checksum(r.debt) != *nhash || Encode(r) !=
        "BLOODBORNE_OWED_V1\n" + std::string(*slot) + "\n" +
        std::string(*fingerprint) + "\n" + std::string(*seq) + "\n" +
        std::string(*length) + "\n" + std::string(*checksum) + "\n" + r.debt) {
        return std::nullopt;
    }
    return r;
}

inline std::optional<Revision> ReadReady(const std::filesystem::path& dir) {
    namespace fs = std::filesystem;
    std::error_code err;
    if (dir.extension() != ".ready" || !fs::is_directory(fs::symlink_status(dir, err)) ||
        err) return std::nullopt;
    const auto file = dir / "ledger.txt";
    err.clear();
    if (!fs::is_regular_file(fs::symlink_status(file, err)) || err) return std::nullopt;
    const auto size = fs::file_size(file, err);
    if (err || size > MaxRecordBytes) return std::nullopt;
    std::ifstream in{file, std::ios::binary};
    if (!in) return std::nullopt;
    const auto data = detail::ReadExactRecord(in, static_cast<std::size_t>(size));
    if (!data) return std::nullopt;
    auto parsed = Decode(*data);
    if (!parsed || dir.filename() != Name(*parsed) + ".ready") return std::nullopt;
    return parsed;
}

// Never silently use an older debt if the newest committed or pending
// revision is corrupt. The game must pause ledger operations until the
// incomplete record is inspected/restored, rather than re-grant an old debt.
enum class ScanStatus { Empty, Ready, Blocked };
struct ScanResult {
    ScanStatus status = ScanStatus::Blocked;
    std::optional<Revision> latest;
};

// Caller MUST hold the exclusive writer lock or obtain it via ScanLatest.
// This internal reader checks every matching revision, including crashed
// candidates and gaps, before selecting any old debt.
namespace detail {
inline ScanResult ScanRevisionsUnlocked(const std::filesystem::path& root, unsigned slot,
                                       std::string_view fingerprint) {
    namespace fs = std::filesystem;
    Revision who{slot, std::string{fingerprint}, 1, ""};
    if (!Valid(who)) return {};
    std::error_code err;
    if (!fs::is_directory(fs::symlink_status(root, err)) || err) return {};
    const std::string prefix = "slot" + std::to_string(slot) + "-" +
                               std::string(fingerprint) + "-r";
    std::optional<Revision> newest;
    // At most 32768 retained revisions per hunter. Fixed-size 4KiB
    // bitset gives O(number of revision files) validation with no heap
    // allocations, sorting or quadratic duplicate searches.
    std::array<std::uint64_t, 512> seen{};
    std::uint64_t count = 0;
    bool blocked = false;
    for (fs::directory_iterator it{root, err}, end; !err && it != end;
         it.increment(err)) {
        const std::string name = it->path().filename().string();
        if (!name.starts_with(prefix)) continue;
        if (it->path().extension() != ".ready") {
            // Includes a crashed .pending directory or an unexpected name
            // matching this character; never ignore a potentially newer debt.
            blocked = true;
            break;
        }
        const auto item = ReadReady(it->path());
        if (!item || item->slot != slot || item->character_fingerprint != fingerprint) {
            blocked = true;
            break;
        }
        // B79: a zero-debt tombstone means "the hunter's items are safely
        // saved". No actual disk-save acknowledgement or stable savedata
        // identity exists in the client yet. A legacy/synthetic committed
        // tombstone must therefore BLOCK replay/recovery, not silently
        // erase outstanding debt. ReadReady/Decode remain available for
        // diagnostics; no confirmed-retirement reader exists yet.
        if (item->debt.empty()) {
            blocked = true;
            break;
        }
        // A deleted intermediate revision or a forged massive sequence
        // creates an ambiguous history: NEVER use a stale previously-paid
        // debt or implicitly fill a gap.
        if (item->sequence == 0 || item->sequence > MaxRevisions || count >= MaxRevisions) {
            blocked = true;
            break;
        }
        const auto offset = item->sequence - 1;
        auto& word = seen[offset / 64];
        const auto mask = std::uint64_t{1} << (offset % 64);
        if ((word & mask) != 0) {
            blocked = true;
            break;
        }
        word |= mask;
        ++count;
        if (!newest || item->sequence > newest->sequence) newest = item;
    }
    if (err || blocked) return {};
    if (!newest) return {ScanStatus::Empty, std::nullopt};
    // All seen sequences are unique positive integers; if the maximum
    // equals count, those integers must be precisely 1, 2, ..., count.
    if (newest->sequence != count) return {};
    return {ScanStatus::Ready, std::move(newest)};
}
} // namespace detail

inline ScanResult ScanLatest(const std::filesystem::path& root, unsigned slot,
                             std::string_view fingerprint) {
    namespace fs = std::filesystem;
    std::error_code err;
    if (!fs::is_directory(fs::symlink_status(root, err)) || err) return {};
    // A check for an existing lock followed by an unlocked scan has a TOCTOU
    // race: another writer may create .pending AFTER the check but BEFORE
    // this reader lists revisions, leading to stale debt replay.
    // Use the SAME exclusive cooperative lock for readers and writers.
    // This is only for offline recovery, NOT a per-frame game-thread scan.
    const auto lock = root / ".writer.lock";
    err.clear();
    if (!fs::create_directory(lock, err) || err) return {};
    const ScanResult result = detail::ScanRevisionsUnlocked(root, slot, fingerprint);
    err.clear();
    if (!fs::remove(lock, err) || err) return {};
    return result;
}

inline bool CreateNewRevision(const std::filesystem::path& root, const Revision& r) {
    namespace fs = std::filesystem;
    // B79: refuse an optimistic paid/empty record until a VERIFIED
    // game-save disk ACK and immutable hunter identity can authorize the
    // retirement. In-memory HeldKeyGoods equality, slot-only metadata or
    // a native void-return GiveItems invocation are NOT that ACK. Keep
    // this writer offline; do not expose a boolean "acknowledged" bypass.
    if (!Valid(r) || r.debt.empty()) return false;
    std::error_code err;
    if (!fs::is_directory(fs::symlink_status(root, err)) || err) return false;
    const auto lock = root / ".writer.lock";
    // Atomic mkdir is an exclusive writer marker; a stale lock blocks until
    // manual recovery, never an automatic delete after a crash.
    err.clear();
    if (!fs::create_directory(lock, err) || err) return false;
    const auto release = [&] {
        std::error_code ignored;
        fs::remove(lock, ignored);
    };
    // Reject replay of an older paid record, a skipped revision number, or
    // attempts to append after a corrupt/pending entry. This check occurs
    // INSIDE the exclusive writer lock to avoid cooperative-writer races.
    const ScanResult last = detail::ScanRevisionsUnlocked(
        root, r.slot, r.character_fingerprint);
    const bool first = last.status == ScanStatus::Empty && r.sequence == 1;
    const bool next = last.status == ScanStatus::Ready && last.latest &&
                      last.latest->sequence < UINT64_MAX &&
                      r.sequence == last.latest->sequence + 1;
    if (!first && !next) {
        release();
        return false;
    }
    const std::string name = Name(r);
    const auto pending = root / (name + ".pending");
    const auto ready = root / (name + ".ready");
    err.clear();
    const auto ready_status = fs::symlink_status(ready, err);
    // Do not overwrite a dangling symlink or non-regular existing path.
    if ((err && err != std::errc::no_such_file_or_directory) ||
        ready_status.type() != fs::file_type::not_found) {
        release();
        return false;
    }
    err.clear();
    if (!fs::create_directory(pending, err) || err) { release(); return false; }
    bool success = false;
    {
        const std::string data = Encode(r);
        std::ofstream out{pending / "ledger.txt", std::ios::binary | std::ios::trunc};
        if (out) {
            out.write(data.data(), static_cast<std::streamsize>(data.size()));
            out.flush();
            success = out.good();
            out.close();
            success = success && out.good();
        }
        if (success) {
            std::ifstream in{pending / "ledger.txt", std::ios::binary};
            // A concurrent append or shrink must not turn verification
            // into an unbounded read or a silently accepted partial record.
            const auto check = detail::ReadExactRecord(in, data.size());
            success = check && Decode(*check) == std::optional{r};
        }
        if (success) {
            err.clear();
            fs::rename(pending, ready, err);
            success = !err && ReadReady(ready) == std::optional{r};
        }
    }
    if (!success) {
        // Remove only this freshly created revision candidate, never an
        // older .ready or the underlying game save. An unexpected .ready
        // is not automatically touched.
        err.clear();
        fs::remove_all(pending, err);
    }
    release();
    return success;
}

} // namespace BloodborneCoop::PhantomKeyLedgerFile
