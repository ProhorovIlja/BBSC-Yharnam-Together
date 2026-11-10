// SPDX-License-Identifier: GPL-2.0-or-later
#include <cassert>
#include <iostream>
#include <vector>
#include "bbcoop/roster_dedup.h"
struct Hunter { char id[40]; char name[40]; int state; int level; };
int main() {
    using BbRoster::AppendUniqueOnline;
    const Hunter team_a{"a","Same name",1,42};
    const Hunter other_copy{"a","Same name",1,0};
    const Hunter other_name{"b","Same name",1,0};
    const Hunter offline{"offline","Offline",0,0};
    const Hunter unknown1{"","Unknown",1,0};
    const Hunter unknown2{"","Unknown",1,0};
    const Hunter other_b{"b","Same name",1,19};
    std::vector<const Hunter*> rows;
    AppendUniqueOnline(rows,team_a,0);
    AppendUniqueOnline(rows,other_copy,0);
    AppendUniqueOnline(rows,other_name,0);
    AppendUniqueOnline(rows,offline,0);
    AppendUniqueOnline(rows,unknown1,0);
    AppendUniqueOnline(rows,unknown2,0);
    AppendUniqueOnline(rows,other_b,0);
    assert(rows.size()==4); // a, b, unknown1, unknown2
    assert(rows[0]==&team_a && rows[0]->level==42); // team info wins
    assert(rows[1]==&other_name);
    assert(rows[2]==&unknown1 && rows[3]==&unknown2);
    for (int i=0;i<100;++i) AppendUniqueOnline(rows,other_copy,0);
    assert(rows.size()==4); // stable page/count after repeated lobby snapshots
    std::cout<<"B46_ROSTER_DUPLICATES_REMOVED_WITHOUT_COLLAPSING_SAME_NAMES_PASS\n";
    return 0;
}
