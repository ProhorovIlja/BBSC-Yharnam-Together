# Ultimate B38: selectable dedicated Global servers with isolated accounts

**2026-11-09**, stacked on [Draft B37 #88](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/88), B37's [CI 3/3 success](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/actions/runs/42680306931). Requested by the project owner: support adding any number of individually hosted **dedicated Global servers**, switching between them from a dropdown instead of treating a remote host as Local; sign-up, login, connection, keys and online count must follow the selected server.

## Source-proven problem

The actual `bbport/launcher/bbport_coop.py` already saves `server_ids` (account ID and signed secret) and `server_keys` (pinned link server public key) **per host address** in `user/coop.json`, but exposes only one editable `global_server` and one **shared** `global_name`. With more than one server the displayed account name can therefore come from an unrelated one, and no UI supports selecting a saved Global address. The login/signup code in `bbport_launcher_win.py` uses `bbport_coop.global_url(self.coop)` for auth and `global_game_settings` for game connection. B37's shard-based online counter uses the same selected URL when `server_type=global`.

## Code changes

1. Preserve `global_server` for backward compatibility with launched games. Add optional `global_servers` list and `server_labels`/ `server_names` dictionaries to `user/coop.json`. Data is derived with `global_profiles`, `add_global_profile`, `select_global_profile`, `remove_global_profile` and `profile_label`. Built-in `https://seamlesshunt.com` always remains as an option. There is no arbitrary short cap on adding dedicated servers.
2. Reject `http://`, credential-bearing URLs, query strings/fragments, malformed hostnames and ports. Canonicalize HTTPS URL using the existing `region_url` predicate, which also supports validated custom HTTPS ports. Profile names are bounded to 64 characters. No `verify=False`, TLS bypass, plaintext credentials in URLs or unaudited remote code download.
3. Each server's account **display name** now lives in `server_names[server_key(url)]`. `signed_in_global` and `signed_out_global` update just that server; legacy old one-server `global_name` is migrated to the original server's key on read. Existing server-specific signed credentials and key pins are preserved, not copied between servers. Removing a custom profile deletes **its locally cached sign-in and pinning**, not a remote server-side account; user confirmation is required.
4. In Tk `build_coop_server`, add a readonly Global-server dropdown plus **Add server / Remove** buttons in the Global section, supporting existing and newly added servers. Selection refreshes the correct authentication view, clears transient password/recovery code inputs, persists settings, and resets B37's online counter to unknown until the new server responds.
5. Reject switching while game is running, preparing or authentication is pending. Bind the source URL into async `coop_auth_answered` callback so a late answer from server A cannot silently overwrite the credentials or display of server B.
6. Shared Bloodborne save files, client patches and official launcher binaries are **not changed based on a server's untrusted response**. Servers can impose compatible protocol and release rules; a selection doesn't imply an arbitrary dedicated host may supply code, game assets or DLC. Owner's offline-edited-save-allowed policy is unchanged.

## Coverage

`bbport/tests/test_global_server_profiles.py` imports real `bbport_coop.py`, validates custom server URLs, duplicates, multiple entries, per-host sign-ins and sign-outs, saved/migrated older settings, removal/key isolation, B37 directory count for chosen URL and source Tk UI behavior. CI runs these on both Windows and Linux, along with B37 tests. Exactly six changed files and three pinned Git blob SHA.

**Pending:** full Windows Tk manual interaction, local-host online player count, port-specific status, TLS error reproduction from [#24](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/issues/24) on user devices, real authenticated signup across multiple live dedicated server implementations, mixed CUSA and gameplay. No Fornex, private save or release tests, no user credentials touched. Remains Draft.
