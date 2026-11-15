// SPDX-License-Identifier: GPL-2.0-or-later
#include <chrono>
#include <clocale>
#include <cwchar>
#include <cstdio>
#include <fstream>
#include "bbport_ngx_paths.h"
namespace fs = std::filesystem;
static void Check(bool ok, int line) {
    if (!ok) { std::fprintf(stderr,"NGX path check failed at %d\n",line); std::exit(1); }
}
#define CHECK(ok) Check((ok),__LINE__)
int main() {
    CHECK(std::setlocale(LC_ALL,"C")!=nullptr);
    const std::string locale=std::setlocale(LC_ALL,nullptr);
    const auto root=fs::temp_directory_path()/std::to_string(
        std::chrono::steady_clock::now().time_since_epoch().count());
    CHECK(fs::create_directory(root));
    const fs::path names[]={"ascii",fs::path(std::u8string(u8"Игры_血缘_🎮"))};
#ifndef _WIN32
    std::mbstate_t legacy_state{};
    const wchar_t* legacy_text=L"\u0418\u0433\u0440\u044b_\u8840\u7f18";
    CHECK(std::wcsrtombs(nullptr,&legacy_text,0,&legacy_state)==static_cast<std::size_t>(-1));
    std::puts("LEGACY_WIDE_TO_MULTIBYTE_UNDER_C=FAILED");
    bool legacy_failed=false;
    try { (void)(root/names[1]).wstring(); }
    catch(const std::exception&) { legacy_failed=true; }
    std::printf("LEGACY_POSIX_WSTRING_UNDER_C=%s\n",legacy_failed ? "FAILED" : "ACCEPTED");
#endif
    unsigned cases=0;
    for (const auto& rt_name:names) for (const auto& dt_name:names) {
        const auto rt=root/"runtime"/rt_name,dt=root/"data"/dt_name;
        fs::create_directories(rt); fs::create_directories(dt);
        {std::ofstream output(rt/"libnvidia-ngx-dlss.so.1");output<<"fixture-library";}
        fs::path staging;
        {
            BbNgxPaths::Paths paths(rt,dt);
            CHECK(locale==std::setlocale(LC_ALL,nullptr));
            CHECK(fs::equivalent(fs::path(paths.Runtime()),rt));
            CHECK(fs::equivalent(fs::path(paths.Data()),dt));
            std::ifstream input(fs::path(paths.Runtime())/"libnvidia-ngx-dlss.so.1");
            std::string bytes; input>>bytes; CHECK(bytes=="fixture-library");
            {std::ofstream output(fs::path(paths.Data())/"ngx-log.txt");output<<"fixture-log";}
            CHECK(fs::is_regular_file(dt/"ngx-log.txt"));
            staging=paths.Staging();
#ifdef _WIN32
            CHECK(staging.empty());
#else
            for(const auto* wide : {&paths.Runtime(), &paths.Data()}) {
                std::mbstate_t state{}; const wchar_t* text=wide->c_str();
                CHECK(std::wcsrtombs(nullptr,&text,0,&state)!=static_cast<std::size_t>(-1));
            }
            for (wchar_t c:paths.Runtime()) CHECK(c>=0 && c<128);
            for (wchar_t c:paths.Data()) CHECK(c>=0 && c<128);
            const bool unicode=rt_name!=names[0] || dt_name!=names[0];
            CHECK(staging.empty()!=unicode);
            if(!staging.empty()){
                CHECK((fs::status(staging).permissions() &
                      (fs::perms::group_all|fs::perms::others_all))==fs::perms::none);
                BbNgxPaths::Paths simultaneous(rt,dt);
                CHECK(simultaneous.Staging()!=staging && fs::exists(staging));
            }
#endif
        }
        CHECK(staging.empty() || !fs::exists(staging));
        CHECK(fs::is_regular_file(rt/"libnvidia-ngx-dlss.so.1"));
        CHECK(fs::is_regular_file(dt/"ngx-log.txt"));
        ++cases;
    }
    bool rejected=false;
    try { BbNgxPaths::Paths missing(root/"missing",root); }
    catch(const std::system_error&) { rejected=true; }
    CHECK(rejected && locale==std::setlocale(LC_ALL,nullptr));
    fs::remove_all(root);
    std::printf("NGX paths: %u ASCII/Unicode combinations, private lifetime, original preservation, "
                "missing-path rejection and C locale passed\n",cases);
}
