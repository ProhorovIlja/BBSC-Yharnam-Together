#include "core/phantom_key_ledger_file.h"

#include <cassert>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
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
    assert(CanonicalDebt(first.debt));
    assert(Decode(Encode(first)) == std::optional{first});
    assert(CreateNewRevision(root, first));
    const fs::path ready1 = root / (Name(first) + ".ready");
    assert(ReadReady(ready1) == std::optional{first});
    assert(ScanLatest(root, 3, identity).status == ScanStatus::Ready);
    assert(ScanLatest(root, 3, identity).latest == std::optional{first});
    assert(ScanLatest(root, 4, identity).status == ScanStatus::Empty);
    assert(!CreateNewRevision(root, first));
    assert(ReadReady(ready1) == std::optional{first});
    assert(!fs::exists(root / ".writer.lock"));

    // One can publish a new revision without ever deleting the old one.
    Revision second{3, identity, 2, "4114 1 1\n4000 1 2\n4110 1 1\n"};
    assert(CreateNewRevision(root, second));
    assert(ReadReady(root / (Name(second) + ".ready")) == std::optional{second});
    assert(ScanLatest(root, 3, identity).latest == std::optional{second});
    assert(ReadReady(ready1) == std::optional{first});

    // An explicit tombstone is a committed entry, not "file went missing".
    Revision cleared{3, identity, 3, ""};
    assert(CreateNewRevision(root, cleared));
    assert(ReadReady(root / (Name(cleared) + ".ready")) == std::optional{cleared});
    assert(ScanLatest(root, 3, identity).latest == std::optional{cleared});
    assert(ReadReady(ready1) == std::optional{first});

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
    Revision damaged{3, identity, 6, "4114 1 1\n"};
    assert(CreateNewRevision(root, damaged));
    const fs::path ready6 = root / (Name(damaged) + ".ready");
    {
        std::ofstream out{ready6 / "ledger.txt", std::ios::binary | std::ios::trunc};
        out << "broken version";
    }
    assert(!ReadReady(ready6));
    assert(ScanLatest(root, 3, identity).status == ScanStatus::Blocked);
    assert(ReadReady(ready1) == std::optional{first});
    Revision other{4, "abcdef0123456789abcdef0123456789", 1, "4114 1 1\n"};
    assert(CreateNewRevision(root, other));
    assert(ReadReady(root / (Name(other) + ".ready")) == std::optional{other});
    assert(ScanLatest(root, 4, other.character_fingerprint).status == ScanStatus::Ready);
    assert(ScanLatest(root, 4, other.character_fingerprint).latest == std::optional{other});
    assert(ReadReady(root / (Name(first) + ".ready")) != std::optional{other});

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
    cleanup();
    std::cout << "B68_PHANTOM_LEDGER_IMMUTABLE_TEST_PASS\n";
}
