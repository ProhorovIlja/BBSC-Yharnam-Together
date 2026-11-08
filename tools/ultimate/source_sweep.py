#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded, paginated GitHub ecosystem evidence inventory; never clones or runs code.

Usage:
  GITHUB_TOKEN=... python3 tools/ultimate/source_sweep.py --output-dir /tmp/ultimate-audit

This is a *discovery tool*, not an exhaustive index of GitHub. GitHub search
limits queries to 1,000 matched results, and a finite request budget deliberately
bounds API calls and report size. Inspect project source/licences before import.
No game archives, private sources, tokens, account data or logs are collected.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SEARCHES = {
    "original-bbhost-and-forks": "bbhost in:name fork:true",
    "bbport-family": "bloodborne_pc in:name fork:true",
    "bloodborne-seamless": "bloodborne seamless co-op in:name,description",
    "shadnet-family": "shadnet in:name fork:true",
    "nightwatch": "NightwatchCoop in:name fork:true",
    "lantern-engine": "LanternEngine in:name fork:true",
    "shadps4-renderer": "shadPS4 in:name fork:true",
    "bloodborne-native": "bloodborne native in:name,description",
    "bloodborne-launchers": "bloodborne launcher in:name,description",
    "bloodborne-mod-tools": "bloodborne mod tools in:name,description",
    "souls-engine-tools": "dark souls III bloodborne engine in:description",
}
SEEDS = (
    "droogie/bbhost",
    "deadinside28/bloodborne_pc",
    "Supermedo/bloodborne_pc",
    "Mrsuss60/bloodborne_pc_windows_port",
    "visy/bloodborne_pc_windows_port",
    "Awakenchan/LanternEngine",
    "vladtepes22/NightwatchCoop",
    "shadps4-emu/shadPS4",
    "shadps4-emu/shadNet",
    "Wozzardman/shadnet-p2p",
    "Amanises-Yharnam-Together/BBSC-Yharnam-Together",
    "bloodborne-native/bloodborne-recomp",
    "bloodborne-native/bloodborne-runtime",
    "bloodborne-native/bbcpu",
)


class RequestLimit(RuntimeError):
    pass


class GitHubAPI:
    def __init__(self, token="", max_requests=100, opener=None):
        self.token = token
        self.max_requests = max_requests
        self.calls = 0
        self.opener = opener or urllib.request.urlopen

    def get(self, path, params=None):
        if self.calls >= self.max_requests:
            raise RequestLimit("request budget reached")
        if not path.startswith("/") or "//" in path or "?" in path:
            raise ValueError("Only plain GitHub REST API paths are allowed")
        self.calls += 1
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "bbsc-ultimate-source-audit/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(url, headers=headers)
        try:
            with self.opener(req, timeout=20) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
                if len(raw) > 4 * 1024 * 1024:
                    raise ValueError("API response too large")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            # Never embed server response: it could contain a URL with private query data.
            raise RuntimeError("GitHub REST HTTP " + str(exc.code)) from None


def compact(item):
    name = item.get("full_name", "")
    if not REPO_RE.fullmatch(name):
        return None
    return {
        "repo": name,
        "html_url": "https://github.com/" + name,
        "description": (item.get("description") or "")[:200],
        "fork": bool(item.get("fork", False)),
        "parent": (item.get("parent") or {}).get("full_name"),
        "license": (item.get("license") or {}).get("spdx_id"),
        "archived": bool(item.get("archived", False)),
        "pushed_at": item.get("pushed_at"),
        "default_branch": item.get("default_branch"),
        "stars": item.get("stargazers_count"),
        "forks": item.get("forks_count"),
        "found_in": [],
        "branches": [],
        "pull_requests": [],
        "issues": [],  # GitHub Issues only, excludes PRs returned from /issues
        "branch_truncated": False,
        "pr_truncated": False,
        "issue_truncated": False,
    }


def scan(api, searches=SEARCHES, seeds=SEEDS, search_pages=2, search_page_size=75,
         inspect_repos=12, branch_pages=2, pr_pages=2, issue_pages=1, max_repos=1500):
    records, scans, warnings = {}, [], []
    halted = False
    for family, query in searches.items():
        found, total, queried_pages, truncated = 0, None, 0, False
        for page in range(1, search_pages + 1):
            try:
                result = api.get("/search/repositories",
                                 {"q": query, "sort": "updated", "order": "desc",
                                  "per_page": search_page_size, "page": page})
            except (RequestLimit, RuntimeError, ValueError) as exc:
                warnings.append(f"{family}: {exc}")
                halted = isinstance(exc, RequestLimit)
                truncated = True
                break
            items = result.get("items", [])
            total = result.get("total_count", total)
            queried_pages += 1
            for item in items:
                r = compact(item)
                if not r:
                    continue
                if r["repo"] not in records and len(records) >= max_repos:
                    truncated = True
                    continue
                target = records.setdefault(r["repo"], r)
                if family not in target["found_in"]:
                    target["found_in"].append(family)
                found += 1
            if len(items) < search_page_size:
                break
            if page == search_pages:
                truncated = True
        scans.append({"family": family, "query": query, "pages": queried_pages,
                      "matched_in_pages": found, "github_total_count": total,
                      "truncated": truncated or bool(total and total > queried_pages * search_page_size),
                      "search_cap_1000": bool(total and total > 1000)})
        if halted:
            break

    order = list(dict.fromkeys([*seeds, *sorted(records)]))
    for name in order[:]:
        if len(records) >= max_repos:
            break
        if name not in records and REPO_RE.fullmatch(name):
            try:
                item = compact(api.get("/repos/" + name))
                if item:
                    item["found_in"].append("explicit-seed")
                    records[name] = item
            except (RequestLimit, RuntimeError, ValueError) as exc:
                warnings.append(f"seed {name}: {exc}")
                if isinstance(exc, RequestLimit):
                    halted = True
                    break

    # Inspect *named original roots first*, not the first search hit.
    selected = [name for name in order if name in records][:inspect_repos]
    for name in selected:
        current = records[name]
        try:
            details = compact(api.get("/repos/" + name))
            if details:
                for field in ("description", "fork", "parent", "license", "archived",
                              "pushed_at", "default_branch", "stars", "forks"):
                    current[field] = details[field]
        except (RequestLimit, RuntimeError, ValueError) as exc:
            warnings.append(f"repo {name}: {exc}")
            if isinstance(exc, RequestLimit):
                halted = True
                break
        for label, count, suffix, per_page in (
                ("branches", branch_pages, "branches", 100),
                ("pull_requests", pr_pages, "pulls", 100),
                ("issues", issue_pages, "issues", 100)):
            for page in range(1, count + 1):
                params = {"per_page": per_page, "page": page}
                if label in ("pull_requests", "issues"):
                    params.update({"state": "all", "sort": "updated", "direction": "desc"})
                try:
                    values = api.get("/repos/" + name + "/" + suffix, params)
                    if not isinstance(values, list):
                        raise ValueError("Expected a list from GitHub")
                except (RequestLimit, RuntimeError, ValueError) as exc:
                    warnings.append(f"{label} {name}: {exc}")
                    current[{"branches": "branch_truncated", "pull_requests": "pr_truncated",
                             "issues": "issue_truncated"}[label]] = True
                    if isinstance(exc, RequestLimit):
                        halted = True
                    break
                for value in values:
                    if label == "branches":
                        current["branches"].append({
                            "name": value.get("name"),
                            "commit": (value.get("commit") or {}).get("sha"),
                        })
                    elif label == "pull_requests":
                        current["pull_requests"].append({
                            "number": value.get("number"),
                            "title": (value.get("title") or "")[:180],
                            "state": value.get("state"),
                            "draft": value.get("draft"),
                            "merged_at": value.get("merged_at"),
                            "updated_at": value.get("updated_at"),
                            "head_sha": ((value.get("head") or {}).get("sha")),
                        })
                    elif not value.get("pull_request"):  # /repos/.../issues includes PRs!
                        # Metadata only: issue bodies, logs, attachments and image URLs are
                        # deliberately not copied into the public CI artifact.
                        number = value.get("number")
                        if not isinstance(number, int) or number < 1:
                            continue
                        current["issues"].append({
                            "number": number,
                            "title": (value.get("title") or "")[:180],
                            "url": current["html_url"] + "/issues/" + str(number),
                            "state": value.get("state"),
                            "state_reason": value.get("state_reason"),
                            "updated_at": value.get("updated_at"),
                            "closed_at": value.get("closed_at"),
                            "comments": value.get("comments", 0),
                            "labels": [str(label.get("name", ""))[:60]
                                       for label in (value.get("labels") or []) if isinstance(label, dict)][:12],
                        })
                if len(values) < per_page:
                    break
                if page == count:
                    current[{"branches": "branch_truncated", "pull_requests": "pr_truncated",
                             "issues": "issue_truncated"}[label]] = True
            if halted:
                break
        if halted:
            break

    return {
        "schema": "bbsc-ultimate-source-audit-v2-with-issues",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "coverage": "BOUNDED_DISCOVERY_NOT_ALL_GITHUB",
        "request_count": api.calls,
        "request_limit": api.max_requests,
        "truncated": halted or any(x["truncated"] for x in scans)
                     or any(x["branch_truncated"] or x["pr_truncated"] or x["issue_truncated"]
                            for x in records.values()),
        "searches": scans,
        "repositories": [records[name] for name in sorted(records)],
        "warnings": warnings[:80],
    }


def markdown(report):
    lines = [
        "# BBSC Ultimate GitHub source sweep",
        "",
        f"Generated: {report['generated_at_utc']}",
        "",
        "**Discovery only**: not proof of playable compatibility, licence clearance,"
        " measured performance, or exhaustive GitHub coverage.",
        "",
        f"Repositories: {len(report['repositories'])}; "
        f"API requests: {report['request_count']}/{report['request_limit']}; "
        f"truncated: {report['truncated']}.",
        "",
        "## Search coverage",
        "",
        "| Family | Pages | Matches in returned pages | Reported total | Truncated |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for s in report["searches"]:
        lines.append(f"| {s['family']} | {s['pages']} | {s['matched_in_pages']} | "
                     f"{s['github_total_count'] or 'unknown'} | {s['truncated']} |")
    lines += ["", "## Selected original runtimes / pinned inspection", "",
              "| Repository | License metadata | Parent | Branches read | PRs read | Issues read |",
              "| --- | --- | --- | ---: | ---: | ---: |"]
    originals = set(SEEDS)
    for r in report["repositories"]:
        if r["repo"] not in originals:
            continue
        lines.append(f"| [\x60{r['repo']}\x60]({r['html_url']}) | "
                     f"{r['license'] or 'unknown'} | {r['parent'] or 'root/unknown'} | "
                     f"{len(r['branches'])} | {len(r['pull_requests'])} | "
                     f"{len(r['issues'])} |")
    lines += ["", "## Warnings", ""]
    lines += ["- " + w.replace("|", "/")[:240] for w in report["warnings"]]
    if not report["warnings"]:
        lines.append("No request failures recorded. Search coverage is still bounded.")
    lines += ["", "Inspect \x60inventory.json\x60 for each candidate and immutable PR head SHA. "
              "Never copy code from repos with unverified licence/ABI or release a test build "
              "without private rig validation.", ""]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--max-requests", type=int, default=100)
    p.add_argument("--search-pages", type=int, default=2)
    p.add_argument("--inspect-repos", type=int, default=12)
    p.add_argument("--branch-pages", type=int, default=2)
    p.add_argument("--pr-pages", type=int, default=2)
    p.add_argument("--issue-pages", type=int, default=1)
    opts = p.parse_args(argv)
    if not (1 <= opts.max_requests <= 350 and 1 <= opts.search_pages <= 10
            and 0 <= opts.inspect_repos <= 30 and 1 <= opts.branch_pages <= 10
            and 1 <= opts.pr_pages <= 10 and 1 <= opts.issue_pages <= 10):
        p.error("invalid bounded audit limits")
    report = scan(GitHubAPI(token=os.environ.get("GITHUB_TOKEN", ""),
                            max_requests=opts.max_requests),
                  search_pages=opts.search_pages, inspect_repos=opts.inspect_repos,
                  branch_pages=opts.branch_pages, pr_pages=opts.pr_pages,
                  issue_pages=opts.issue_pages)
    target = Path(opts.output_dir)
    target.mkdir(parents=True, exist_ok=True)
    data = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if len(data.encode("utf-8")) > 2_000_000:
        raise SystemExit("Inventory exceeds 2 MB; reduce request budget and inspect in batches")
    (target / "inventory.json").write_text(data, encoding="utf-8")
    (target / "index.md").write_text(markdown(report), encoding="utf-8")
    print(f"SWEEP_RECORDED repos={len(report['repositories'])} "
          f"issues={sum(len(r['issues']) for r in report['repositories'])} "
          f"api_calls={report['request_count']} warnings={len(report['warnings'])} "
          f"truncated={report['truncated']}")
    return 0 if report["repositories"] else 2


if __name__ == "__main__":
    sys.exit(main())
