// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Phase 11, one port: a game's TCP calls through the server link's Rpc stream
// (coop/rpc_tunnel.h), and the limits on what the other side of a stream
// (coop/coop_stream.h, coop/game_link.h) can make shadNet hold.
#include <iostream>
#include <string>
#include <vector>

#include "coop/rpc_tunnel.h"
#include "src/rpc_write_budget.h"

namespace {

using BloodborneCoop::CoopStream;
using BloodborneCoop::GameFrame;
using BloodborneCoop::GameLinkPeer;
using BloodborneCoop::PacketClass;
using BloodborneCoop::RpcTunnel;
using Event = RpcTunnel::Event;

bool Check(bool condition, const char *expression, int line) {
  if (!condition) {
    std::cerr << "check failed at line " << line << ": " << expression << '\n';
  }
  return condition;
}

#define CHECK(expression)                                                      \
  do {                                                                         \
    if (!Check((expression), #expression, __LINE__))                           \
      return 1;                                                                \
  } while (false)

std::vector<u8> Bytes(const std::string &text) {
  return {text.begin(), text.end()};
}

// Everything `from` has to send, delivered to `to`: the events there.
std::vector<Event> Carry(RpcTunnel &from, RpcTunnel &to, s64 now_ms) {
  std::vector<Event> events;
  for (const auto &body : from.Flush(now_ms)) {
    for (Event &event : to.Receive(body, now_ms)) {
      events.push_back(std::move(event));
    }
  }
  // The acks back.
  for (const auto &body : to.Flush(now_ms)) {
    from.Receive(body, now_ms);
  }
  return events;
}

int AConnectionGoesThrough() {
  RpcTunnel game{"game", 7};
  RpcTunnel server{"shadnet", 9};
  game.Open(0);
  game.Write(Bytes("login"), 0);
  std::vector<Event> events = Carry(game, server, 0);
  CHECK(events.size() == 2);
  CHECK(events[0].kind == Event::Kind::Opened);
  CHECK(events[1] == (Event{Event::Kind::Data, Bytes("login")}));
  CHECK(server.IsOpen() && game.IsOpen());

  // A large answer comes whole and in order.
  std::string reply(5000, 'r');
  reply[4999] = 'z';
  server.Write(Bytes(reply), 10);
  events = Carry(server, game, 10);
  std::string got;
  for (const Event &event : events) {
    CHECK(event.kind == Event::Kind::Data);
    got.append(event.bytes.begin(), event.bytes.end());
  }
  CHECK(got == reply);
  CHECK(game.Unacked() == 0 && server.Unacked() == 0);

  // Nothing to say: Write of nothing sends nothing.
  server.Write({}, 20);
  CHECK(Carry(server, game, 20).empty());

  game.Close(30);
  events = Carry(game, server, 30);
  CHECK(events.size() == 1 && events[0].kind == Event::Kind::Closed);
  CHECK(!server.IsOpen() && !game.IsOpen());
  std::cout << "rpc tunnel: a connection goes through\n";
  return 0;
}

int FreshRpcFragmentsDrainInBoundedSlices() {
  RpcTunnel game{"game", 7};
  RpcTunnel server{"shadnet", 9};
  game.Open(0);
  CHECK(Carry(game, server, 0).size() == 1);
  const auto reply = Bytes(std::string(100 * 1024, 'r') + "tail");
  server.Write(reply, 1);
  server.Close(1);
  const auto initial = server.UnackedBytes();
  std::vector<u8> got;
  bool closed = false;
  for (s64 tick = 2; tick < 100 && !closed; ++tick) {
    const auto frames = server.Flush(tick, 7);
    CHECK(!frames.empty());
    size_t fragments = 0;
    for (const auto& body : frames) {
      const auto decoded = BloodborneCoop::DecodeGameFrame(body);
      CHECK(decoded.has_value());
      fragments += decoded->entries.size();
      for (const auto& event : game.Receive(body, tick)) {
        CHECK(!closed);
        if (event.kind == Event::Kind::Closed) {
          closed = true;
        } else {
          CHECK(event.kind == Event::Kind::Data);
          got.insert(got.end(), event.bytes.begin(), event.bytes.end());
        }
      }
    }
    CHECK(fragments <= 7);
    for (const auto& ack : game.Flush(tick))
      server.Receive(ack, tick);
    if (tick == 2)
      CHECK(server.UnackedBytes() > 0 && server.UnackedBytes() < initial && !closed);
  }
  CHECK(closed && got == reply && server.UnackedBytes() == 0);
  return 0;
}

int ALostDatagramIsSentAgain() {
  RpcTunnel game{"game", 7};
  RpcTunnel server{"shadnet", 9};
  game.Open(0);
  game.Write(Bytes("hello"), 0);
  (void)game.Flush(0); // lost on the way
  CHECK(Carry(game, server, 50).empty());
  const std::vector<Event> events = Carry(game, server, 400);
  CHECK(events.size() == 2 && events[1].bytes == Bytes("hello"));
  std::cout << "rpc tunnel: a lost datagram is sent again\n";
  return 0;
}

// The server restarted (a new instance): the game's connection through it is
// over, and the game's next one starts on the new server.
int ARestartedServerEndsTheConnection() {
  RpcTunnel game{"game", 7};
  RpcTunnel server{"shadnet", 9};
  game.Open(0);
  Carry(game, server, 0);
  server.Write(Bytes("hi"), 5);
  Carry(server, game, 5);
  CHECK(game.IsOpen());

  RpcTunnel restarted{"shadnet", 10};
  restarted.Write({},
                  100); // nothing; its keepalive is what the game hears first
  std::vector<Event> events;
  for (s64 now = 1100; now < 3000 && events.empty(); now += 100) {
    events = Carry(restarted, game, now);
  }
  CHECK(events.size() == 1 && events[0].kind == Event::Kind::PeerRestarted);
  CHECK(!game.IsOpen());

  game.Open(4000);
  game.Write(Bytes("login"), 4000);
  events = Carry(game, restarted, 4000);
  CHECK(events.size() == 2 && events[0].kind == Event::Kind::Opened);
  std::cout << "rpc tunnel: a restarted server ends the connection\n";
  return 0;
}

int RestartAfterCloseRetiresBackendBeforeNextOpen() {
  RpcTunnel game{"game", 7};
  RpcTunnel server{"shadnet", 9};
  game.Open(0);
  CHECK(Carry(game, server, 0).size() == 1);
  game.Close(10);
  CHECK(Carry(game, server, 10) == (std::vector<Event>{{Event::Kind::Closed, {}}}));
  CHECK(!server.IsOpen());
  RpcTunnel restarted{"game", 8};
  // New process heartbeat can reach the server before its TCP connection.
  CHECK(Carry(restarted, server, 1100) ==
        (std::vector<Event>{{Event::Kind::PeerRestarted, {}}}));
  CHECK(!server.IsOpen());
  CHECK(Carry(restarted, server, 2200).empty());
  restarted.Open(2300);
  CHECK(Carry(restarted, server, 2300) ==
        (std::vector<Event>{{Event::Kind::Opened, {}}}));
  return 0;
}

int RestartedGameRetiresOldBackendBeforeOpeningNewOne() {
  RpcTunnel game{"game", 7};
  RpcTunnel server{"shadnet", 9};
  game.Open(0);
  CHECK(Carry(game, server, 0).size() == 1);
  RpcTunnel restarted{"game", 8};
  restarted.Open(20);
  restarted.Write(Bytes("fresh"), 20);
  const std::vector<Event> expected{{Event::Kind::PeerRestarted, {}},
                                    {Event::Kind::Opened, {}},
                                    {Event::Kind::Data, Bytes("fresh")}};
  CHECK(Carry(restarted, server, 20) == expected);
  game.Write(Bytes("old"), 30);
  CHECK(Carry(game, server, 30).empty());
  CHECK(server.IsOpen());
  restarted.Close(40);
  CHECK(Carry(restarted, server, 40) == (std::vector<Event>{{Event::Kind::Closed, {}}}));
  return 0;
}

CoopStream::Limits SmallLimits() {
  CoopStream::Limits limits;
  limits.message_bytes = 4000;
  limits.chunk_bytes = CoopStream::ChunkBytes + 1;
  limits.held_bytes = 3000;
  limits.unreliable_channels = 4;
  return limits;
}

// A message past the limit breaks the stream: nothing of it is kept, and
// nothing more is taken.
int AMessagePastTheLimitBreaksTheStream() {
  CoopStream game{"game", 7};
  CoopStream server{"shadnet", 9, SmallLimits()};
  game.Send(std::vector<u8>(3999, 'a'), 0);
  size_t taken = 0;
  for (const auto &body : game.Flush(0)) {
    taken += server.Receive(body, 0).size();
  }
  CHECK(taken == 1 && !server.Broken());
  // A message that never ends (no LastChunk) is a message past the limit too.
  game.Send(std::vector<u8>(4001, 'b'), 10);
  for (const auto &body : game.Flush(10)) {
    taken += server.Receive(body, 10).size();
  }
  CHECK(taken == 1);
  CHECK(server.Broken());
  CHECK(server.HeldBytes() == 0);
  game.Send(Bytes("later"), 20);
  for (const auto &body : game.Flush(20)) {
    taken += server.Receive(body, 20).size();
  }
  CHECK(taken == 1);
  std::cout << "streams: a message past the limit breaks the stream\n";
  return 0;
}

// A chunk larger than any Send makes breaks it at once.
int AChunkLargerThanASendsBreaksTheStream() {
  GameLinkPeer raw{"game", 7};
  CoopStream server{"shadnet", 9, SmallLimits()};
  std::vector<u8> chunk(CoopStream::ChunkBytes + 2, 'c');
  chunk[0] = CoopStream::LastChunk;
  raw.Send(PacketClass::Reliable, chunk, 0);
  for (const GameFrame &frame : raw.Flush(0)) {
    CHECK(server.Receive(EncodeGameFrame(frame), 0).empty());
  }
  CHECK(server.Broken());
  std::cout << "streams: a chunk larger than a Send makes breaks the stream\n";
  return 0;
}

// Chunks out of order are held up to held_bytes; past it they are dropped and
// come again as resends, and every message still arrives, in order.
int OutOfOrderChunksAreHeldUpToTheLimit() {
  CoopStream game{"game", 7};
  CoopStream server{"shadnet", 9, SmallLimits()};
  for (int index = 0; index < 10; ++index) {
    game.Send(std::vector<u8>(900, static_cast<u8>('0' + index)), 0);
  }
  std::vector<std::vector<u8>> bodies = game.Flush(0);
  CHECK(bodies.size() == 10);
  std::vector<std::vector<u8>> taken;
  for (size_t index = 1; index < bodies.size(); ++index) { // the first is lost
    for (auto &message : server.Receive(bodies[index], 0)) {
      taken.push_back(std::move(message));
    }
    CHECK(server.HeldBytes() <= 3000);
  }
  CHECK(taken.empty());
  for (s64 now = 100; now < 20'000 && taken.size() < 10; now += 100) {
    for (const auto &body : game.Flush(now)) {
      for (auto &message : server.Receive(body, now)) {
        taken.push_back(std::move(message));
      }
      CHECK(server.HeldBytes() <= 3000);
    }
    for (const auto &body : server.Flush(now)) {
      game.Receive(body, now);
    }
  }
  CHECK(taken.size() == 10);
  for (size_t index = 0; index < taken.size(); ++index) {
    CHECK(taken[index] == std::vector<u8>(900, static_cast<u8>('0' + index)));
  }
  CHECK(server.HeldBytes() == 0 && game.UnackedBytes() == 0);
  std::cout << "streams: chunks out of order are held up to the limit\n";
  return 0;
}

// Unreliable packets: the newest per channel, on so many channels.
int UnreliableChannelsAreCapped() {
  GameLinkPeer::Settings settings;
  settings.unreliable_channels = 4;
  GameLinkPeer game{"game", 7};
  GameLinkPeer server{"shadnet", 9, settings};
  for (u8 channel = 0; channel < 10; ++channel) {
    game.Send(PacketClass::Unreliable, std::vector<u8>{channel, 0, 0, 0, 1}, 0);
  }
  size_t delivered = 0;
  for (const GameFrame &frame : game.Flush(0)) {
    delivered += server.Receive(frame, 0).size();
  }
  CHECK(delivered == 4);
  std::cout << "streams: unreliable channels are capped\n";
  return 0;
}

// The bytes not yet acked, for the server to drop a member that never acks.
int UnackedBytesAreCounted() {
  CoopStream server{"shadnet", 9};
  CoopStream game{"game", 7};
  server.Send(std::vector<u8>(2500, 'x'), 0);
  CHECK(server.UnackedBytes() == 2503); // three chunks, each with its byte
  for (const auto &body : server.Flush(0)) {
    game.Receive(body, 0);
  }
  CHECK(server.UnackedBytes() == 2503);
  for (const auto &body : game.Flush(0)) {
    server.Receive(body, 0);
  }
  CHECK(server.UnackedBytes() == 0);
  std::cout << "streams: unacked bytes are counted\n";
  return 0;
}

// The Rpc tunnel's limits are its stream's.
int AnRpcMessagePastTheLimitBreaksTheTunnel() {
  RpcTunnel game{"game", 7};
  RpcTunnel server{"shadnet", 9, SmallLimits()};
  game.Open(0);
  game.Write(std::vector<u8>(5000, 'd'), 0);
  Carry(game, server, 0);
  CHECK(server.Broken());
  std::cout << "rpc tunnel: a message past the limit breaks the tunnel\n";
  return 0;
}

int ProductionReplyLimitsRejectOversizedFragmentsAndMessages() {
  const auto limits = RpcTunnel::TransportLimits();
  RpcTunnel game{"game", 7, limits};
  RpcTunnel server{"shadnet", 9, limits};
  game.Open(0);
  CHECK(Carry(game, server, 0).size() == 1);
  const std::vector<u8> normal(RpcTunnel::MaxDataBytes, 'r');
  server.Write(normal, 1);
  CHECK(Carry(server, game, 1) == (std::vector<Event>{{Event::Kind::Data, normal}}));

  CoopStream raw{"shadnet", 9};
  RpcTunnel bounded{"game", 7, limits};
  raw.Send(std::vector<u8>(limits.message_bytes + 1, 'x'), 0);
  for (const auto& frame : raw.Flush(0)) CHECK(bounded.Receive(frame, 0).empty());
  CHECK(bounded.Broken());

  GameLinkPeer bad{"shadnet", 9};
  bounded = RpcTunnel{"game", 11, limits};
  std::vector<u8> fragment(limits.chunk_bytes + 1, 'x');
  fragment[0] = CoopStream::LastChunk;
  bad.Send(PacketClass::Reliable, fragment, 0);
  for (const auto& frame : bad.Flush(0)) CHECK(bounded.Receive(EncodeGameFrame(frame), 0).empty());
  CHECK(bounded.Broken());
  return 0;
}

int FreshClientTunnelRecoversAfterInvalidReply() {
  RpcTunnel game{"game", 7, SmallLimits()};
  RpcTunnel server{"shadnet", 9};
  game.Open(0);
  CHECK(Carry(game, server, 0).size() == 1);
  server.Write(std::vector<u8>(5000, 'x'), 1);
  const auto bad = server.Flush(1);
  CHECK(!bad.empty());
  for (const auto& frame : bad) CHECK(game.Receive(frame, 1).empty());
  CHECK(game.Broken());

  // The bridge drops the old TCP connection and constructs a fresh instance.
  game = RpcTunnel{"game", 11, SmallLimits()};
  for (const auto& frame : bad) CHECK(game.Receive(frame, 2).empty());
  CHECK(!game.Broken() && !game.IsOpen());
  game.Open(3);
  game.Write(Bytes("login"), 3);
  const std::vector<Event> opening{{Event::Kind::PeerRestarted, {}},
                                   {Event::Kind::Opened, {}},
                                   {Event::Kind::Data, Bytes("login")}};
  CHECK(Carry(game, server, 3) == opening);
  server.Write(Bytes("ok"), 4);
  CHECK(Carry(server, game, 4) == (std::vector<Event>{{Event::Kind::Data, Bytes("ok")}}));
  return 0;
}

int ClosedTunnelDoesNotDeliverData() {
  RpcTunnel game{"game", 7};
  RpcTunnel server{"shadnet", 9};
  server.Write(Bytes("before open"), 0);
  CHECK(server.Unacked() == 0 && server.UnackedBytes() == 0);
  CHECK(Carry(server, game, 0).empty());
  game.Open(1);
  CHECK(Carry(game, server, 1).size() == 1);
  server.Write(Bytes("active"), 2);
  CHECK(Carry(server, game, 2) == (std::vector<Event>{{Event::Kind::Data, Bytes("active")}}));
  server.Close(3);
  const auto close_bytes = server.UnackedBytes();
  const auto close_frames = server.Unacked();
  CHECK(close_bytes == 2 && close_frames == 1);
  server.Write(Bytes("after close"), 3);
  CHECK(server.UnackedBytes() == close_bytes && server.Unacked() == close_frames);
  CHECK(Carry(server, game, 3) == (std::vector<Event>{{Event::Kind::Closed, {}}}));
  game.Open(4);
  CHECK(Carry(game, server, 4).size() == 1);
  server.Write(Bytes("reopened"), 5);
  CHECK(Carry(server, game, 5) == (std::vector<Event>{{Event::Kind::Data, Bytes("reopened")}}));
  std::cout << "rpc tunnel: only active TCP connections receive data\n";
  return 0;
}

int RpcControlMessagesWithTrailingBytesDoNotChangeState() {
  CoopStream raw{"game", 7};
  RpcTunnel server{"shadnet", 9};
  const auto deliver = [&](std::initializer_list<u8> bytes, s64 now) {
    raw.Send(std::vector<u8>(bytes), now);
    std::vector<Event> events;
    for (const auto& body : raw.Flush(now)) {
      auto batch = server.Receive(body, now);
      for (auto& event : batch) events.push_back(std::move(event));
    }
    for (const auto& body : server.Flush(now)) raw.Receive(body, now);
    return events;
  };
  CHECK(deliver({1, 99}, 0).empty() && !server.IsOpen());
  CHECK(deliver({1}, 1) == (std::vector<Event>{{Event::Kind::Opened, {}}}));
  CHECK(deliver({1, 99}, 2).empty() && server.IsOpen());
  CHECK(deliver({3, 99}, 3).empty() && server.IsOpen());
  CHECK(deliver({2, 'x'}, 4) == (std::vector<Event>{{Event::Kind::Data, Bytes("x")}}));
  CHECK(deliver({3}, 5) == (std::vector<Event>{{Event::Kind::Closed, {}}}));
  CHECK(!server.IsOpen());
  return 0;
}

int RequestBudgetReservesCloseAndRecoversAfterAck() {
  BloodborneCoop::RpcReadPause pause;
  CHECK(!pause.Expired(0));
  CHECK(!pause.Expired(4999));
  CHECK(pause.Expired(5000));
  pause.Reset();
  CHECK(!pause.Expired(6000));
  CHECK(pause.Expired(11000));
  RpcTunnel game{"game", 7}, server{"shadnet", 9};
  const auto data = Bytes("abc");
  constexpr size_t budget = 9; // Open (2), Data (5), Close (2).
  CHECK(!game.CanWriteRequest(data.size(), budget));
  CHECK(!game.TryWrite(data, 0, budget));
  CHECK(!game.TryOpen(0, 3) && game.UnackedBytes() == 0);
  CHECK(game.TryOpen(0, budget));
  CHECK(!game.CanWriteRequest(data.size(), budget - 1));
  CHECK(game.CanWriteRequest(data.size(), budget));
  CHECK(!game.TryWrite(data, 0, budget - 1) && game.UnackedBytes() == 2);
  CHECK(game.TryWrite(data, 0, budget) && game.UnackedBytes() == 7);
  CHECK(!game.CanWriteRequest(1, budget));
  CHECK(!game.TryWrite(Bytes("x"), 0, budget) && game.UnackedBytes() == 7);
  Carry(game, server, 0);
  CHECK(game.UnackedBytes() == 0);
  CHECK(game.CanWriteRequest(data.size(), budget));
  CHECK(game.TryOpen(0, budget));
  CHECK(game.TryWrite(data, 0, budget));
  game.Close(0);
  CHECK(game.UnackedBytes() == budget);
  for (int retry = 0; retry < 100; ++retry)
    CHECK(!game.TryOpen(1, budget) && game.UnackedBytes() == budget);
  const auto events = Carry(game, server, 1);
  CHECK(events.size() == 3 && events[1] == (Event{Event::Kind::Data, data}));
  CHECK(events[2].kind == Event::Kind::Closed && game.UnackedBytes() == 0);
  CHECK(game.TryOpen(2, budget));
  CHECK(Carry(game, server, 2) == (std::vector<Event>{{Event::Kind::Opened, {}}}));
  return 0;
}

int BackendWriteBudgetIsCheckedBeforeBuffering() {
  using ShadNetRpc::FitsWriteBudget;
  constexpr auto limit = 1 << 20;
  CHECK(FitsWriteBudget(0, limit, limit));
  CHECK(FitsWriteBudget(limit - 1, 1, limit));
  CHECK(!FitsWriteBudget(limit - 1, 2, limit));
  CHECK(!FitsWriteBudget(limit + 1, 0, limit));
  CHECK(!FitsWriteBudget(-1, 1, limit));
  CHECK(!FitsWriteBudget(0, -1, limit));
  CHECK(!FitsWriteBudget(INT64_MAX, INT64_MAX, INT64_MAX));
  std::cout << "rpc tunnel: local backend write budget boundaries passed\n";
  return 0;
}

int CoalescedReplyStaysWithinMessageAndQueueBounds() {
  RpcTunnel server{"shadnet", 9};
  RpcTunnel game{"game", 7, {.message_bytes = 64 * 1024}};
  game.Open(0);
  Carry(game, server, 0);
  const std::vector<u8> bytes(RpcTunnel::MaxDataBytes * 4 + 1000, 'r');
  const auto exact = bytes.size() + 4 * 18 + 3;
  CHECK(!server.CanQueueWrite(bytes.size(), exact - 1));
  CHECK(server.CanQueueWrite(bytes.size(), exact));
  CHECK(!server.CanQueueWrite(SIZE_MAX, SIZE_MAX));
  CHECK(server.UnackedBytes() == 0);
  server.Write(bytes, 1);
  CHECK(server.UnackedBytes() == exact && !server.CanQueueWrite(1, exact));
  std::vector<u8> got;
  const auto events = Carry(server, game, 1);
  CHECK(events.size() == 5 && !game.Broken());
  for (const auto& event : events) {
    CHECK(event.kind == Event::Kind::Data && event.bytes.size() <= RpcTunnel::MaxDataBytes);
    got.insert(got.end(), event.bytes.begin(), event.bytes.end());
  }
  CHECK(got == bytes && server.UnackedBytes() == 0);
  std::cout << "rpc tunnel: coalesced TCP reply, exact queue budget and byte order passed\n";
  return 0;
}

} // namespace

int main() {
  if (AConnectionGoesThrough() != 0 || ALostDatagramIsSentAgain() != 0 ||
      FreshRpcFragmentsDrainInBoundedSlices() != 0 ||
      ARestartedServerEndsTheConnection() != 0 ||
      RestartedGameRetiresOldBackendBeforeOpeningNewOne() != 0 ||
      RestartAfterCloseRetiresBackendBeforeNextOpen() != 0 ||
      AMessagePastTheLimitBreaksTheStream() != 0 ||
      AChunkLargerThanASendsBreaksTheStream() != 0 ||
      OutOfOrderChunksAreHeldUpToTheLimit() != 0 ||
      UnreliableChannelsAreCapped() != 0 || UnackedBytesAreCounted() != 0 ||
      AnRpcMessagePastTheLimitBreaksTheTunnel() != 0 ||
      FreshClientTunnelRecoversAfterInvalidReply() != 0 ||
      ProductionReplyLimitsRejectOversizedFragmentsAndMessages() != 0 ||
      CoalescedReplyStaysWithinMessageAndQueueBounds() != 0 ||
      RequestBudgetReservesCloseAndRecoversAfterAck() != 0 ||
      BackendWriteBudgetIsCheckedBeforeBuffering() != 0 ||
      RpcControlMessagesWithTrailingBytesDoNotChangeState() != 0 ||
      ClosedTunnelDoesNotDeliverData() != 0) {
    return 1;
  }
  return 0;
}
