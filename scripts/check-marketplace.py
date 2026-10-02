#!/usr/bin/env python3
"""Check .claude-plugin/marketplace.json against this repo's publishing contract.

Fails when an entry pins a ref or sha, uses a source kind other than github or
git-subdir, names a plugin whose own plugin.json disagrees, sits in a repo that
carries its own marketplace.json, or declares a dependency range that no
`<dep>--vX.Y.Z` tag on the dependency's repo satisfies. Reads public GitHub over
HTTPS; needs no token.

Usage: check-marketplace.py [MARKETPLACE_JSON]
       check-marketplace.py --selftest
"""
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

MARKETPLACE = "moneymike-plugins"
RAW = "https://raw.githubusercontent.com/{repo}/HEAD/{path}"


def parse_partial(text):
    text = text.strip().lstrip("v=")
    if text in ("", "*", "x", "X"):
        return []
    parts = []
    for p in text.split("."):
        if p in ("x", "X", "*"):
            break
        parts.append(int(p))
    return parts


def full(parts):
    return tuple(parts + [0] * (3 - len(parts)))


def bump(parts, index):
    out = list(parts[: index + 1])
    out[index] += 1
    return full(out)


def comparator(token):
    """One npm-style comparator token, returned as a list of (op, version) bounds."""
    m = re.match(r"^(\^|~|>=|<=|>|<|=)?(.*)$", token)
    op, rest = m.group(1) or "", m.group(2)
    parts = parse_partial(rest)
    if op == "^":
        if not parts:
            return []
        lo = full(parts)
        first = next((i for i, v in enumerate(lo) if v != 0), len(parts) - 1)
        first = min(first, len(parts) - 1)
        return [(">=", lo), ("<", bump(parts, first))]
    if op == "~":
        if not parts:
            return []
        return [(">=", full(parts)), ("<", bump(parts, 1 if len(parts) >= 2 else 0))]
    if op in (">=", ">", "<", "<="):
        if not parts:
            return [] if op in (">=", "<=") else [("<", (0, 0, 0))]
        if op == ">" and len(parts) < 3:
            return [(">=", bump(parts, len(parts) - 1))]
        if op == "<=" and len(parts) < 3:
            return [("<", bump(parts, len(parts) - 1))]
        return [(op, full(parts))]
    if not parts:
        return []
    if len(parts) == 3:
        return [("=", full(parts))]
    return [(">=", full(parts)), ("<", bump(parts, len(parts) - 1))]


def satisfies(version, rng):
    v = full(parse_partial(version))
    ops = {">=": v.__ge__, ">": v.__gt__, "<": v.__lt__, "<=": v.__le__, "=": v.__eq__}
    for alternative in rng.split("||"):
        bounds = [b for tok in alternative.split() for b in comparator(tok)]
        if all(ops[op](bound) for op, bound in bounds):
            return True
    return False


def fetch(repo, path):
    try:
        with urllib.request.urlopen(RAW.format(repo=repo, path=path), timeout=30) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ""


def tag_versions(repo, name):
    out = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", f"https://github.com/{repo}", f"refs/tags/{name}--v*"],
        check=True, capture_output=True, text=True, timeout=60,
    ).stdout
    return [line.rsplit(f"{name}--v", 1)[1] for line in out.splitlines() if f"{name}--v" in line]


def check(path):
    errors = []
    with open(path) as f:
        market = json.load(f)
    plugins = market.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        return ["plugins must be a non-empty array"]
    names = [p.get("name") for p in plugins]
    for dup in sorted({n for n in names if names.count(n) > 1}):
        errors.append(f"duplicate plugin name {dup!r}")
    repos = {}
    for p in plugins:
        name, src = p.get("name"), p.get("source") or {}
        if "ref" in src or "sha" in src:
            errors.append(f"{name}: entries carry no ref or sha; installs track the default branch")
        kind = src.get("source")
        if kind == "github":
            repo, sub = src.get("repo"), ""
        elif kind == "git-subdir":
            repo, sub = src.get("url"), (src.get("path") or "").strip("/") + "/"
        else:
            errors.append(f"{name}: source kind {kind!r} is not github or git-subdir")
            continue
        repos[name] = repo
        status, body = fetch(repo, f"{sub}.claude-plugin/plugin.json")
        if status != 200:
            errors.append(f"{name}: {repo}/{sub}.claude-plugin/plugin.json not readable (HTTP {status})")
            continue
        manifest = json.loads(body)
        if manifest.get("name") != name:
            errors.append(f"{name}: plugin.json names itself {manifest.get('name')!r}")
        status, _ = fetch(repo, ".claude-plugin/marketplace.json")
        if status != 404:
            errors.append(f"{name}: {repo} carries its own marketplace.json (HTTP {status}); publish only through this file")
        p["_deps"] = manifest.get("dependencies") or []
    for p in plugins:
        for dep in p.get("_deps", []):
            dname, rng = dep.get("name"), dep.get("version", "*")
            if dep.get("marketplace", MARKETPLACE) != MARKETPLACE:
                print(f"skip {p['name']} -> {dname}: published elsewhere")
                continue
            if dname not in repos:
                errors.append(f"{p['name']}: depends on {dname!r}, which this marketplace does not list")
                continue
            versions = tag_versions(repos[dname], dname)
            hits = [v for v in versions if satisfies(v, rng)]
            if hits:
                print(f"ok {p['name']} -> {dname} {rng}: {dname}--v{max(hits, key=lambda v: full(parse_partial(v)))}")
            else:
                errors.append(f"{p['name']}: no {dname}--vX.Y.Z tag on {repos[dname]} satisfies {rng!r} "
                              f"(found {', '.join(sorted(versions)) or 'none'})")
    return errors


def selftest():
    cases = [
        ("1.6.0", "^1.3.0", True), ("2.0.0", "^1.3.0", False), ("1.2.9", "^1.3.0", False),
        ("0.1.5", "^0.1.0", True), ("0.2.0", "^0.1.0", False), ("0.0.3", "^0.0.3", True),
        ("0.0.4", "^0.0.3", False), ("1.4.9", "~1.4.0", True), ("1.5.0", "~1.4.0", False),
        ("1.9.0", ">=1.x <2.0.0", True), ("2.0.0", ">=1.x <2.0.0", False), ("1.2.0", "1.x", True),
        ("1.2.3", "1.2.3", True), ("1.2.4", "1.2.3", False), ("3.0.0", "^1.0.0 || ^3.0.0", True),
        ("5.0.0", "*", True), ("1.0.0", "<1.0.0", False),
    ]
    bad = [(v, r, want) for v, r, want in cases if satisfies(v, r) != want]
    for v, r, want in bad:
        print(f"FAIL satisfies({v!r}, {r!r}) != {want}", file=sys.stderr)
    print(f"selftest: {len(cases) - len(bad)}/{len(cases)} ok")
    return 1 if bad else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    errs = check(sys.argv[1] if len(sys.argv) > 1 else ".claude-plugin/marketplace.json")
    for e in errs:
        print(f"marketplace: {e}", file=sys.stderr)
    print("marketplace: ok" if not errs else f"marketplace: {len(errs)} problem(s)")
    sys.exit(1 if errs else 0)
