// SPDX-License-Identifier: GPL-2.0-or-later
// bbport co-op: what the Discord status says and reads (discord_activity.h).
#include <cassert>
#include <cstdio>
#include "gpu/bbcoop/discord_activity.h"

using namespace DiscordActivity;

int main() {
    // A forged/local pipe header must not allocate gigabytes or use an
    // unexpected opcode. Boundary cap is a client policy, not a Discord spec.
    assert(ValidIpcFrame(0, 0));
    assert(ValidIpcFrame(1, MaxIpcPayloadBytes));
    assert(ValidIpcFrame(4, 16));
    assert(!ValidIpcFrame(1, MaxIpcPayloadBytes + 1));
    assert(!ValidIpcFrame(1, UINT32_MAX));
    assert(!ValidIpcFrame(5, 0));

    assert(Json("Yharnam") == "\"Yharnam\"");
    assert(Json("a\"b\\c") == "\"a\\\"b\\\\c\"");
    assert(Json("line\nbreak") == "\"line break\"");

    const std::string join = "{\"evt\":\"ACTIVITY_JOIN\",\"data\":{\"secret\":\"c:ABC\\\"D\"}}";
    assert(Field(join, "evt") == "ACTIVITY_JOIN");
    assert(Field(join, "secret") == "c:ABC\"D");
    assert(Field(join, "nothing").empty());
    const std::string ask = "{\"id\":\"1\",\"data\":{\"user\":{\"id\":\"42\",\"username\":\"ada\"}}}";
    assert(Field(ask, "id") == "1");
    assert(Field(ask, "id", ask.find("\"user\"")) == "42");

    // JSON encoders are allowed to put whitespace after the colon.
    assert(Field(R"({"evt" : "ACTIVITY_JOIN","data" : { "secret" : "c:JOIN" }})", "evt") ==
           "ACTIVITY_JOIN");
    assert(Field(R"({"evt" : "ACTIVITY_JOIN","data" : { "secret" : "c:JOIN" }})", "secret") ==
           "c:JOIN");

    // Do not find keys inside a string value with escaped quotes.
    assert(Field(R"({"message":"ignore \"evt\":\"BAD\"","evt":"ACTIVITY_JOIN"})", "evt") ==
           "ACTIVITY_JOIN");
    assert(Field(R"({"message":"only \"evt\":\"BAD\""})", "evt").empty());

    // Unicode names survive JSON \u escapes, including emoji surrogate pairs.
    assert(Field(R"({"username":"Caf\u00e9 \uD83D\uDC7B"})", "username") ==
           "Caf\xc3\xa9 \xf0\x9f\x91\xbb");
    assert(Field(R"({"username":"bad \uD83D"})", "username").empty());
    assert(Field(R"({"username":"bad \uXYZ1"})", "username").empty());
    assert(Field(R"({"username":"bad \q"})", "username").empty());

    const std::string nested = R"({"id":"1","data": { "user" : {"id" : "42", "username": "Ada"} }})";
    assert(Field(nested, "id") == "1");
    assert(Field(nested, "id", nested.find("\"user\"")) == "42");

    constexpr int Invite = 0, Ask = 1, Open = 2;
    assert(JoinSecret("KTCDAB", "t1", Invite, Invite, 2, 5) == "c:KTCDAB"); // the leader
    assert(JoinSecret("", "t1", Open, Invite, 2, 5) == "t:t1");
    assert(JoinSecret("", "t1", Ask, Invite, 2, 5) == "t:t1");
    assert(JoinSecret("", "t1", Invite, Invite, 2, 5).empty()) ; // a member of a closed team
    assert(JoinSecret("KTCDAB", "t1", Open, Invite, 5, 5).empty()); // full
    // Deterministic parser stress: preserve each byte of a quoted string
    // except ASCII control bytes, which Json() normalizes to spaces.
    // Malformed frames must never read out of bounds.
    std::uint32_t seed = 0x91A2B3C4u;
    const auto next = [&seed] {
        seed ^= seed << 13;
        seed ^= seed >> 17;
        seed ^= seed << 5;
        return seed;
    };
    for (unsigned round = 0; round < 4096; ++round) {
        std::string raw;
        const unsigned count = next() % 200;
        for (unsigned i = 0; i < count; ++i) {
            raw.push_back(static_cast<char>(next() % 256));
        }
        std::string expected = raw;
        for (char& c : expected) {
            if (static_cast<unsigned char>(c) < 0x20) c = ' ';
        }
        assert(Field(std::string{"{\\\"value\\\":"} + Json(raw) + "}", "value") == expected);
        (void)Field(raw, "value"); // may be any malformed byte sequence
    }

    std::puts("discord activity: ok");
    return 0;
}
