// SPDX-License-Identifier: GPL-2.0-or-later
#include <cassert>
#include <iostream>
#include <string>
#include "bbcoop/roster_filter.h"
using BbRoster::FoldPlayerSearch;
using BbRoster::MatchesPlayerSearch;
int main() {
    assert(MatchesPlayerSearch("ОХОТНИК", "охотник"));
    assert(MatchesPlayerSearch("ЁЖИК-ХАНТЕР", "ёжик"));
    assert(MatchesPlayerSearch("ЛОВКОСТЬ", "лоВКоСТЬ"));
    assert(MatchesPlayerSearch("Hunter Дима", "HUNTER дИма"));
    assert(MatchesPlayerSearch("ÉLITE", "élite"));
    assert(MatchesPlayerSearch("ΑΘΗΝΑ", "αθηνα"));
    assert(MatchesPlayerSearch("ΣΟΣ", "σος")); // Greek final sigma casefold
    assert(MatchesPlayerSearch("GREAT HUNTER", ""));
    assert(MatchesPlayerSearch("Охотник", "ОХОТ"));
    assert(!MatchesPlayerSearch("Охотник", "аркан"));
    assert(!MatchesPlayerSearch("Hunter", "Other"));
    assert(!MatchesPlayerSearch("Игрок", "ИгрокX"));
    assert(FoldPlayerSearch("🐺 Ё").find("ё") != std::string::npos);
    const std::string damaged{"ABC\xFF\xC0\xAF", 6};
    assert(FoldPlayerSearch(damaged).substr(0,3) == "abc");
    assert(FoldPlayerSearch(damaged).size() == damaged.size());
    const std::string unfinished{"AB\xE2\x82", 4};
    assert(FoldPlayerSearch(unfinished).size() == 4);
    std::cout << "B47_UTF8_RU_CYRILLIC_GREEK_LATIN_PLAYER_FILTER_PASS\n";
}
