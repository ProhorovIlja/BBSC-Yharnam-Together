#include "core/phantom_key_ledger_file.h"

#include <cassert>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <system_error>

namespace fs = std::filesystem;
using BloodborneCoop::PhantomKeyLedgerFile::CanonicalDebt;
using BloodborneCoop::PhantomKeyLedgerFile::CreateNewRevision;
using BloodborneCoop::PhantomKeyLedgerFile::Decode;
using BloodborneCoop::PhantomKeyLedgerFile::Encode;
using BloodborneCoop::PhantomKeyLedgerFile::Name;
using BloodborneCoop::PhantomKeyLedgerFile::ReadReady;
using BloodborneCoop::PhantomKeyLedgerFile::Revision;
using BloodborneCoop::PhantomKeyLedgerFile::ScanLatest;
using BloodborneCoop::PhantomKeyLedgerFile::ScanStatus;
using BloodborneCoop::PhantomKeyLedgerFile::Valid;

int main() {
    const auto unique = std::chrono::steady_clock::now().time_since_epoch().count();
    const fs::path root = fs::temp_directory_path() /
                          ("ultimate-b68-owed-ledger-" + std::to_string(unique));
    assert(fs::create_directory(root));
    const auto cleanup = [&] { std::error_code ec; fs::remove_all(root, ec); };
    const std::string identity = "0123456789abcdef0123456789abcdef";
    Revision first{3, identity, 1, "4114 1 1\n4000 1 2\n"};
    assert(Valid(first));
    // B78: disk revision ownership must accept exactly the same retail
    // slots 0-9 as the live phantom and deferred reward owner gates.
    for (unsigned retail_slot = 0; retail_slot < 10; ++retail_slot) {
        Revision retail = first;
        retail.slot = retail_slot;
        assert(Valid(retail));
        assert(Decode(Encode(retail)) == std::optional{retail});
    }
    for (unsigned unsupported_slot : {10u, 11u, 63u, 64u, 1024u}) {
        Revision invalid_owner = first;
        invalid_owner.slot = unsupported_slot;
        assert(!Valid(invalid_owner));
        assert(!Decode(Encode(invalid_owner)));
        assert(!CreateNewRevision(root, invalid_owner));
        assert(ScanLatest(root, unsupported_slot, identity).status == ScanStatus::Blocked);
    }
    assert(CanonicalDebt(first.debt));
    assert(Decode(Encode(first)) == std::optional{first});
    // B73: simulate a file changing AFTER file_size() but BEFORE read:
    // the actual production stream helper must not read arbitrary bytes,
    // accept a truncated record, or ignore trailing appended data.
    const std::string bytes = Encode(first);
    {
        std::istringstream exact{bytes};
        assert(BloodborneCoop::PhantomKeyLedgerFile::detail::ReadExactRecord(
                   exact, bytes.size()) == std::optional{bytes});
    }
    {
        std::istringstream grown{bytes + "EXTRA"};
        assert(!BloodborneCoop::PhantomKeyLedgerFile::detail::ReadExactRecord(
            grown, bytes.size()));
    }
    {
        std::istringstream shrunk{bytes.substr(0, bytes.size() - 1)};
        assert(!BloodborneCoop::PhantomKeyLedgerFile::detail::ReadExactRecord(
            shrunk, bytes.size()));
    }
    {
        std::istringstream oversized{bytes};
        assert(!BloodborneCoop::PhantomKeyLedgerFile::detail::ReadExactRecord(
            oversized, BloodborneCoop::PhantomKeyLedgerFile::MaxRecordBytes + 1));
    }
    assert(CreateNewRevision(root, first));
    const fs::path ready1 = root / (Name(first) + ".ready");
    assert(ReadReady(ready1) == std::optional{first});
    assert(ScanLatest(root, 3, identity).status == ScanStatus::Ready);
    assert(ScanLatest(root, 3, identity).latest == std::optional{first});
    // Offline readers now use the same exclusive lock as writers, and must
    // release it after a successful complete scan.
    assert(!fs::exists(root / ".writer.lock"));
    assert(ScanLatest(root, 4, identity).status == ScanStatus::Empty);
    assert(!fs::exists(root / ".writer.lock"));
    assert(!CreateNewRevision(root, first));
    assert(ReadReady(ready1) == std::optional{first});
    assert(!fs::exists(root / ".writer.lock"));

    // One can publish a new revision without ever deleting the old one.
    Revision second{3, identity, 2, "4114 1 1\n4000 1 2\n4110 1 1\n"};
    assert(CreateNewRevision(root, second));
    assert(ReadReady(root / (Name(second) + ".ready")) == std::optional{second});
    assert(ScanLatest(root, 3, identity).latest == std::optional{second});
    assert(ReadReady(ready1) == std::optional{first});

    // B79: without a verified game-save disk ACK, the offline API cannot
    // infer "paid and saved" from an in-RAM inventory observation. Deny
    // tombstone publishing BEFORE taking the lock or making a directory.
    Revision cleared{3, identity, 3, ""};
    assert(Valid(cleared));  // old wire bytes still decode for diagnosis
    assert(Decode(Encode(cleared)) == std::optional{cleared});
    assert(!CreateNewRevision(root, cleared));
    assert(!fs::exists(root / (Name(cleared) + ".ready")));
    assert(!fs::exists(root / (Name(cleared) + ".pending")));
    assert(!fs::exists(root / ".writer.lock"));
    assert(ScanLatest(root, 3, identity).latest == std::optional{second});
    Revision third{3, identity, 3, "4114 1 1\\n4000 1 2\\n4110 1 1\\n"};
    assert(CreateNewRevision(root, third));
    assert(ReadReady(root / (Name(third) + ".ready")) == std::optional{third});
    assert(ScanLatest(root, 3, identity).latest == std::optional{third});
    assert(ReadReady(ready1) == std::optional{first});

    // A legacy/fabricated empty .ready record must never be silently
    // interpreted as a durable save-confirmed receipt by the scanner.
    // Do not delete or rewrite that record on encountering it.
    const fs::path tomb_root = root / "isolated-unproven-tombstone";
    assert(fs::create_directory(tomb_root));
    Revision tomb1{0, identity, 1, "4114 1 1\\n"};
    Revision tomb2{0, identity, 2, ""};
    assert(CreateNewRevision(tomb_root, tomb1));
    assert(!CreateNewRevision(tomb_root, tomb2));
    const fs::path fake_ready = tomb_root / (Name(tomb2) + ".ready");
    assert(fs::create_directory(fake_ready));
    {
        std::ofstream out{fake_ready / "ledger.txt", std::ios::binary};
        out << Encode(tomb2);
        assert(out.good());
    }
    assert(ReadReady(fake_ready) == std::optional{tomb2}); // inspect only
    assert(ScanLatest(tomb_root, 0, identity).status == ScanStatus::Blocked);
    assert(ScanLatest(tomb_root, 0, identity).latest == std::nullopt);
    assert(!CreateNewRevision(tomb_root, Revision{0, identity, 3, "4000 1 1\\n"}));
    assert(ReadReady(tomb_root / (Name(tomb1) + ".ready")) == std::optional{tomb1});
    assert(!fs::exists(tomb_root / ".writer.lock"));

    // Crash / previous writer still active: do not steal a stale lock.
    assert(fs::create_directory(root / ".writer.lock"));
    Revision later{3, identity, 4, "4110 1 1\n"};
    assert(!CreateNewRevision(root, later));
    assert(ScanLatest(root, 3, identity).status == ScanStatus::Blocked);
    assert(!fs::exists(root / (Name(later) + ".ready")));
    assert(fs::remove(root / ".writer.lock"));
    // An unreadable dangling lock is NOT an unlocked journal.
    std::error_code link_ec;
    fs::create_symlink(root / "not-existing", root / ".writer.lock", link_ec);
    if (!link_ec) {
        assert(ScanLatest(root, 3, identity).status == ScanStatus::Blocked);
        assert(!CreateNewRevision(root, later));
        assert(fs::is_symlink(fs::symlink_status(root / ".writer.lock")));
        fs::remove(root / ".writer.lock");
    }

    assert(CreateNewRevision(root, later));
    // A writer may NEVER skip a sequence or create an older confirmed
    // record after a third revision. The writer checks this under its lock.
    assert(!CreateNewRevision(root, first));
    assert(!CreateNewRevision(root, cleared));
    Revision skipped{3, identity, 9, "4114 1 1\n"};
    assert(!CreateNewRevision(root, skipped));
    assert(!fs::exists(root / (Name(skipped) + ".ready")));
    assert(ScanLatest(root, 3, identity).latest == std::optional{later});

    // An incomplete staged record must never be mistaken for a .ready file.
    Revision interrupted{3, identity, 5, "4114 1 1\n"};
    assert(fs::create_directory(root / (Name(interrupted) + ".pending")));
    assert(!CreateNewRevision(root, interrupted));
    assert(!fs::exists(root / (Name(interrupted) + ".ready")));
    assert(ScanLatest(root, 3, identity).status == ScanStatus::Blocked);
    // The destination may be a dangling symlink; create_directory/rename
    // must never claim it is unused or destroy that pre-existing path.
    Revision occupied{3, identity, 7, "4114 1 1\n"};
    link_ec.clear();
    const auto occupied_path = root / (Name(occupied) + ".ready");
    fs::create_symlink(root / "missing-ledger-target", occupied_path, link_ec);
    if (!link_ec) {
        assert(!CreateNewRevision(root, occupied));
        assert(fs::is_symlink(fs::symlink_status(occupied_path)));
        fs::remove(occupied_path);
    }
    // A prior valid revision is NOT silently replayed when newer debt
    // may be stranded in an interrupted pending transaction.
    assert(ScanLatest(root, 4, identity).status == ScanStatus::Empty);

    // Corrupt bytes, wrong checksum and a renamed other character all fail.
    Revision damaged{3, identity, 5, "4114 1 1\n"};
    assert(!CreateNewRevision(root, damaged));
    assert(fs::remove_all(root / (Name(interrupted) + ".pending")) == 1);
    assert(CreateNewRevision(root, damaged));
    const fs::path ready6 = root / (Name(damaged) + ".ready");
    {
        std::ofstream out{ready6 / "ledger.txt", std::ios::binary | std::ios::trunc};
        out << "broken version";
    }
    assert(!ReadReady(ready6));
    assert(ScanLatest(root, 3, identity).status == ScanStatus::Blocked);
    assert(ReadReady(ready1) == std::optional{first});
    Revision blocked_after_corruption{3, identity, 6, "4110 1 1\n"};
    assert(!CreateNewRevision(root, blocked_after_corruption));
    assert(!fs::exists(root / (Name(blocked_after_corruption) + ".ready")));
    Revision other{4, "abcdef0123456789abcdef0123456789", 1, "4114 1 1\n"};
    assert(CreateNewRevision(root, other));
    assert(ReadReady(root / (Name(other) + ".ready")) == std::optional{other});
    assert(ScanLatest(root, 4, other.character_fingerprint).status == ScanStatus::Ready);
    assert(ScanLatest(root, 4, other.character_fingerprint).latest == std::optional{other});
    assert(ReadReady(root / (Name(first) + ".ready")) != std::optional{other});

    // If an earlier revision disappears, even two individually valid
    // remaining records must not be accepted as a contiguous history.
    const fs::path gap_root = root / "isolated-gap-case";
    assert(fs::create_directory(gap_root));
    Revision gap1{1, identity, 1, "4114 1 1\n"};
    Revision gap2{1, identity, 2, "4114 1 1\n"};
    Revision gap3{1, identity, 3, "4114 1 1\n"};
    assert(CreateNewRevision(gap_root, gap1));
    assert(CreateNewRevision(gap_root, gap2));
    assert(CreateNewRevision(gap_root, gap3));
    assert(ScanLatest(gap_root, 1, identity).latest == std::optional{gap3});
    assert(fs::remove_all(gap_root / (Name(gap2) + ".ready")) == 2);
    assert(ScanLatest(gap_root, 1, identity).status == ScanStatus::Blocked);
    Revision gap4{1, identity, 4, "4110 1 1\n"};
    assert(!CreateNewRevision(gap_root, gap4));
    assert(ReadReady(gap_root / (Name(gap1) + ".ready")) == std::optional{gap1});
    assert(ReadReady(gap_root / (Name(gap3) + ".ready")) == std::optional{gap3});

    // A NEW character with the same slot may start its own sequence 1
    // without seeing another hunter's committed key debt.
    Revision new_hunter{3, "fedcba9876543210fedcba9876543210", 1, "4000 1 1\n"};
    assert(CreateNewRevision(root, new_hunter));
    assert(ScanLatest(root, 3, new_hunter.character_fingerprint).latest ==
           std::optional{new_hunter});

    // B71: the writer must never publish sequence 32769, because readers
    // reject histories beyond the bounded 32768-revision bitmap. A writer
    // that accepted it could permanently block its own character journal.
    Revision at_limit = first;
    at_limit.sequence = 32768;
    assert(Valid(at_limit));
    assert(!CreateNewRevision(root, at_limit)); // a gap still fails closed
    Revision beyond_limit = first;
    beyond_limit.sequence = 32769;
    assert(!Valid(beyond_limit));
    assert(!CreateNewRevision(root, beyond_limit));
    assert(!fs::exists(root / (Name(beyond_limit) + ".pending")));
    assert(!fs::exists(root / (Name(beyond_limit) + ".ready")));
    // Even an externally fabricated beyond-cap .ready record blocks reads.
    const fs::path bound_root = root / "isolated-cap-case";
    assert(fs::create_directory(bound_root));
    Revision bounded_first{2, identity, 1, "4114 1 1\n"};
    assert(CreateNewRevision(bound_root, bounded_first));
    assert(fs::create_directory(bound_root / (Name(beyond_limit) + ".ready")));
    {
        std::ofstream out{bound_root / (Name(beyond_limit) + ".ready") / "ledger.txt",
                          std::ios::binary};
        out << Encode(beyond_limit);
    }
    assert(ScanLatest(bound_root, 2, identity).status == ScanStatus::Ready);
    assert(ScanLatest(bound_root, 3, identity).status == ScanStatus::Blocked);
    assert(!CreateNewRevision(bound_root, Revision{3, identity, 1, "4114 1 1\n"}));
    assert(!fs::exists(bound_root / ".writer.lock"));

    // Refuse invalid item / bell, junk, overlarge, overflow and identity.
    for (const std::string bad : {"200 1 1\n", "4114 0 1\n", "4114 2 1\n",
                                  "4114 1 1", "4114 1 1\njunk\n", "0 1 1\n",
                                  "4114 1 1\n4114 1 1\n",
                                  "4114 01 1\n", "4114 -1 1\n"}) {
        assert(!CanonicalDebt(bad));
    }
    assert(!CanonicalDebt(std::string(65537, 'a')));
    Revision invalid = first;
    invalid.sequence = 0;
    assert(!Valid(invalid));
    assert(!CreateNewRevision(root, invalid));
    invalid = first;
    invalid.character_fingerprint = "../other-character";
    assert(!Valid(invalid));
    assert(!CreateNewRevision(root, invalid));

    // A linked revision directory cannot be read; refusal is portable when
    // the Windows runner permits symlink creation (otherwise skip subcase).
    const auto link = root / "fake.ready";
    std::error_code ec;
    fs::create_directory_symlink(ready1, link, ec);
    if (!ec) {
        assert(!ReadReady(link));
        fs::remove(link);
    }
    assert(ReadReady(ready1) == std::optional{first});
    // The scanner must refuse symlink roots before it creates ANY lock in
    // the linked directory; optional on restricted Windows runner accounts.
    const auto root_link = root / "shortcut";
    ec.clear();
    fs::create_directory_symlink(gap_root, root_link, ec);
    if (!ec) {
        assert(ScanLatest(root_link, 1, identity).status == ScanStatus::Blocked);
        assert(!fs::exists(gap_root / ".writer.lock"));
        fs::remove(root_link);
    }
    // On-disk metadata larger than the hard cap is rejected without reading
    // the payload. This is an isolated fake revision, never a user's save.
    const Revision inflated{2, identity, 1, "4114 1 1\n"};
    const auto huge_dir = root / (Name(inflated) + ".ready");
    assert(fs::create_directory(huge_dir));
    {
        std::ofstream out{huge_dir / "ledger.txt", std::ios::binary};
        out << std::string(BloodborneCoop::PhantomKeyLedgerFile::MaxRecordBytes + 1, 'X');
    }
    assert(!ReadReady(huge_dir));
    assert(ScanLatest(root, 2, identity).status == ScanStatus::Blocked);
    assert(!fs::exists(root / ".writer.lock"));

    // After all normal, failed and incomplete read attempts, a successful
    // read never leaves its cooperative directory lock behind.
    assert(!fs::exists(root / ".writer.lock"));
    cleanup();
    std::cout << "B68_PHANTOM_LEDGER_IMMUTABLE_TEST_PASS\n";
}
