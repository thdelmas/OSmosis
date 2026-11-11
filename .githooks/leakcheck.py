#!/usr/bin/env python3
"""leakcheck: block references that point outside the repository.

Rules (text files only; binaries, lockfiles, vendored and generated trees are skipped):
  escape       a dot-dot path that, resolved from the file's own directory, leaves the repo root   BLOCK
  identity     a path naming a person's machine: /home/<user>, /Users/<user>, /mnt/c/Users/, agent scratch dirs   BLOCK
               (users from <config>/identity-users.txt; other /home/<x> is WARN, BLOCK with --strict-home or client tier)
  homeref      `~/` or `$HOME` references                                                          WARN
  exempt       repos listed in <config>/exempt-repos.txt (the top of the hierarchy) get only the secret rule
  private-url  URL into a repository listed in <config>/private-urls.txt                           BLOCK
  secret       hardcoded secret values (AWS, OpenAI/Anthropic, GitHub, Slack, Google, PEM, generic) BLOCK
  wordlist     regexes from <config>/wordlist.txt, one per line (private; never ship in a repo)     BLOCK

Tier: read from the origin remote. Orgs listed in <config>/own-orgs.txt are "own"; any other org
is "client", where other-home becomes BLOCK. No remote: own. --strict-home does the same anywhere
(use it in a committed hook and in CI, where no config exists).

Config dir: $LEAKCHECK_CONFIG or ~/.config/leakcheck (optional; absent files disable their rule).
Per-repo path ignores: a `.leakcheck-ignore` file at the repo root, one glob per line (fixtures,
test corpora). Paths only; there is no inline override. Fix a hit by moving the reference.

Modes:
  leakcheck --staged [--repo DIR]        staged content (pre-commit)
  leakcheck --tree   [--repo DIR]        every tracked file (CI, audits)
  leakcheck --push-range [--repo DIR]    pre-push: reads the hook's stdin, checks only the pushed changes
  leakcheck --files F... [--repo DIR]    given paths
  leakcheck --hook-claude                Claude Code PreToolUse hook (Write/Edit/Bash) on stdin JSON

Exit: 0 clean, 1 blocked, 2 blocked in --hook-claude (Claude Code's block code).
"""

import fnmatch
import json
import os
import re
import subprocess
import sys

VERSION = "0.1.0"
SKIP_PATH = re.compile(
    r"(^|/)(node_modules|vendor|dist|build|\.git|__pycache__|\.venv|venv|target|\.next|coverage)(/|$)"
    r"|(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|poetry\.lock|go\.sum|composer\.lock)$"
    r"|\.(png|jpe?g|gif|webp|svg|ico|pdf|woff2?|ttf|otf|eot|mp[34]|wav|zip|gz|tgz|jar|apk|aab|jks|p12|min\.(js|css)|map)$",
    re.I,
)
MAX_BYTES = 1_000_000

RE_ESCAPE = re.compile(r"(?<![\w.$])(?:\.\./)+[\w./@+-]*")
RE_HOMEREF = re.compile(r"(?<![\w])~/|\$HOME\b|\$\{HOME\}")
RE_ANYHOME = re.compile(r"(?<![\w])/home/([A-Za-z0-9_-]+)")
RE_IDENTITY_FIXED = re.compile(
    r"(?<![\w])(/Users/[A-Za-z0-9_-]+|/mnt/c/Users/[A-Za-z0-9_-]+|/tmp/cla"
    + r"ude-[\w-]*)"
)
RE_SECRET_FIXED = re.compile(  # case-sensitive vendor prefixes, never inside a longer token
    r"(?<![A-Za-z0-9/+_-])(AKIA[0-9A-Z]{16}|sk-(ant-)?[A-Za-z0-9_-]{20,}|gh[pos]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,})(?![A-Za-z0-9/+])|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
RE_SECRET_KV = re.compile(
    r"\b(api[_-]?key|secret|password|passwd|token|access[_-]?key)\s*[:=]\s*['\"](?!(test|example|dummy|changeme|placeholder|xxx|your[_-]))[A-Za-z0-9_+/-]{16,}['\"]",
    re.I,
)


def find_secret(line):
    return RE_SECRET_FIXED.search(line) or RE_SECRET_KV.search(line)


RE_URL = re.compile(r"https?://[^\s)\]'\"<>]+|git@[\w.-]+:[\w./-]+")


def sh(args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True)
    return r.returncode, r.stdout


def config_dir():
    return os.environ.get("LEAKCHECK_CONFIG") or os.path.expanduser(
        "~/.config/leakcheck"
    )


def read_list(name):
    p = os.path.join(config_dir(), name)
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf8") as f:
        return [
            ln.rstrip("\n")
            for ln in f
            if ln.strip() and not ln.lstrip().startswith("#")
        ]


def repo_root(start):
    rc, out = sh(["git", "-C", start, "rev-parse", "--show-toplevel"])
    return os.path.realpath(out.decode().strip()) if rc == 0 and out.strip() else None


def repo_tier(root, own_orgs):
    rc, out = sh(["git", "-C", root, "remote", "get-url", "origin"])
    if rc != 0:
        return "own"
    m = re.search(r"[:/]([^/:]+)/[^/]+?(?:\.git)?/?$", out.decode().strip())
    org = m.group(1).lower() if m else ""
    return "own" if (not own_orgs or org in own_orgs) else "client"


def is_text(data):
    return b"\0" not in data[:8000]


class Checker:
    def __init__(self, root, tier="own", strict_home=False):
        self.root = root
        self.tier = tier
        self.strict_home = strict_home
        self.exempt = any(
            os.path.realpath(os.path.expanduser(e)) == root
            for e in read_list("exempt-repos.txt")
        )
        self.wordlist = [re.compile(w) for w in read_list("wordlist.txt")]
        self.private_urls = [u.lower() for u in read_list("private-urls.txt")]
        users = read_list("identity-users.txt") or [
            u for u in os.environ.get("LEAKCHECK_IDENTITY_USERS", "").split(",") if u
        ]
        self.identity_users = [u.lower() for u in users]
        self.ignores = []
        ig = os.path.join(root, ".leakcheck-ignore")
        if os.path.isfile(ig):
            with open(ig, encoding="utf8") as f:
                self.ignores = [
                    ln.strip() for ln in f if ln.strip() and not ln.startswith("#")
                ]
        self.findings = []  # (severity, path, lineno, rule, snippet)

    def skip(self, rel):
        if SKIP_PATH.search(rel):
            return True
        return any(
            fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(rel, g.rstrip("/") + "/*")
            for g in self.ignores
        )

    def add(self, sev, rel, n, rule, snippet):
        if rule == "other-home" and (self.tier == "client" or self.strict_home):
            sev = "BLOCK"
        self.findings.append((sev, rel, n, rule, snippet.strip()[:140]))

    def check_text(self, rel, text):
        filedir = os.path.dirname(os.path.join(self.root, rel))
        for n, line in enumerate(text.splitlines(), 1):
            m = find_secret(line)
            if m:
                self.add("BLOCK", rel, n, "secret", m.group(0)[:12] + "…")
            if (
                self.exempt
            ):  # top of the hierarchy (the personal KB): only secrets are checked
                continue
            for m in RE_ESCAPE.finditer(line):
                tok = m.group(0)
                target = os.path.realpath(os.path.join(filedir, tok))
                if not (target == self.root or target.startswith(self.root + os.sep)):
                    self.add("BLOCK", rel, n, "escape", tok)
            for m in RE_IDENTITY_FIXED.finditer(line):
                self.add("BLOCK", rel, n, "identity", m.group(0))
            for m in RE_ANYHOME.finditer(line):
                user = m.group(1).lower()
                hit = any(user == u or user.startswith(u) for u in self.identity_users)
                self.add(
                    "BLOCK" if hit else "WARN",
                    rel,
                    n,
                    "identity" if hit else "other-home",
                    m.group(0),
                )
            if RE_HOMEREF.search(line):
                self.add("WARN", rel, n, "homeref", RE_HOMEREF.search(line).group(0))
            if self.private_urls:
                for m in RE_URL.finditer(line):
                    u = m.group(0).lower()
                    if any(p in u for p in self.private_urls):
                        self.add("BLOCK", rel, n, "private-url", m.group(0))
            for w in self.wordlist:
                m = w.search(line)
                if m:
                    self.add("BLOCK", rel, n, "wordlist", m.group(0))

    def check_blob(self, rel, data):
        if self.skip(rel) or len(data) > MAX_BYTES or not is_text(data):
            return
        self.check_text(rel, data.decode("utf8", "replace"))

    def staged(self):
        rc, out = sh(
            [
                "git",
                "-C",
                self.root,
                "diff",
                "--cached",
                "--name-only",
                "--diff-filter=ACMR",
                "-z",
            ]
        )
        for rel in filter(None, out.decode("utf8", "replace").split("\0")):
            rc, data = sh(["git", "-C", self.root, "show", ":" + rel])
            if rc == 0:
                self.check_blob(rel, data)

    def tree(self):
        rc, out = sh(["git", "-C", self.root, "ls-files", "-z"])
        for rel in filter(None, out.decode("utf8", "replace").split("\0")):
            p = os.path.join(self.root, rel)
            if os.path.isfile(p) and not os.path.islink(p):
                with open(p, "rb") as f:
                    self.check_blob(rel, f.read())

    def push_range(self, lines):
        """pre-push stdin: '<local ref> <local sha> <remote ref> <remote sha>' per line; checks only the
        files that change in each pushed range, at their pushed content."""
        for ln in lines:
            parts = ln.split()
            if len(parts) != 4:
                continue
            lref, lsha, rref, rsha = parts
            if set(lsha) == {"0"}:
                continue  # deletion
            if set(rsha) == {"0"}:
                rc, out = sh(
                    ["git", "-C", self.root, "ls-tree", "-r", "--name-only", "-z", lsha]
                )
            else:
                rc, out = sh(
                    [
                        "git",
                        "-C",
                        self.root,
                        "diff",
                        "--name-only",
                        "--diff-filter=ACMR",
                        "-z",
                        rsha,
                        lsha,
                    ]
                )
                if (
                    rc != 0
                ):  # remote sha unknown locally (rewritten remote): fall back to the whole tree
                    rc, out = sh(
                        [
                            "git",
                            "-C",
                            self.root,
                            "ls-tree",
                            "-r",
                            "--name-only",
                            "-z",
                            lsha,
                        ]
                    )
            for rel in filter(None, out.decode("utf8", "replace").split("\0")):
                rc, data = sh(["git", "-C", self.root, "show", f"{lsha}:{rel}"])
                if rc == 0:
                    self.check_blob(rel, data)

    def files(self, paths):
        for p in paths:
            ap = os.path.realpath(p)
            rel = os.path.relpath(ap, self.root)
            if os.path.isfile(ap):
                with open(ap, "rb") as f:
                    self.check_blob(rel, f.read())

    def report(self, out=sys.stderr):
        blocks = [f for f in self.findings if f[0] == "BLOCK"]
        warns = [f for f in self.findings if f[0] == "WARN"]
        for sev, rel, n, rule, snip in blocks + warns:
            print(f"{sev} {rel}:{n} [{rule}] {snip}", file=out)
        if blocks:
            print(
                f"leakcheck: {len(blocks)} blocking reference(s) outside the repo ({self.tier} tier). "
                f"Move the reference; there is no inline override.",
                file=out,
            )
        return 1 if blocks else 0


def hook_claude():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    tool = ev.get("tool_name", "")
    ti = ev.get("tool_input", {}) or {}
    cwd = ev.get("cwd") or os.getcwd()
    own = [o.lower() for o in read_list("own-orgs.txt")]
    if tool in ("Write", "Edit", "MultiEdit"):
        fp = ti.get("file_path") or ""
        if not fp:
            return 0
        root = repo_root(
            os.path.dirname(fp) if os.path.isdir(os.path.dirname(fp)) else cwd
        )
        if not root or not os.path.realpath(fp).startswith(root + os.sep):
            return 0
        content = ti.get("content")
        if content is None:
            content = ti.get("new_string", "")
            if "edits" in ti:
                content = "\n".join(e.get("new_string", "") for e in ti["edits"])
        c = Checker(root, repo_tier(root, own))
        rel = os.path.relpath(os.path.realpath(fp), root)
        if not c.skip(rel):
            c.check_text(rel, content)
        return 2 if c.report() else 0
    if tool == "Bash":
        cmd = ti.get("command", "")
        if not re.search(r"\bgit\b[^|;&]*\b(commit|push)\b", cmd):
            return 0
        m = re.search(r"\bgit\s+(?:-c\s+\S+\s+)*-C\s+(\S+)", cmd) or re.search(
            r"(?:^|&&|;)\s*cd\s+(\S+)", cmd
        )
        if m:
            cwd = os.path.join(cwd, os.path.expanduser(m.group(1).strip("'\"")))
        root = repo_root(cwd)
        if not root:
            return 0
        c = Checker(root, repo_tier(root, own))
        if re.search(r"\bgit\b[^|;&]*\bpush\b", cmd):
            rc, up = sh(["git", "-C", root, "rev-parse", "--verify", "-q", "@{u}"])
            if rc == 0:
                rc, out = sh(
                    [
                        "git",
                        "-C",
                        root,
                        "diff",
                        "--name-only",
                        "--diff-filter=ACMR",
                        "-z",
                        up.decode().strip(),
                        "HEAD",
                    ]
                )
                for rel in filter(None, out.decode("utf8", "replace").split("\0")):
                    rc2, data = sh(["git", "-C", root, "show", "HEAD:" + rel])
                    if rc2 == 0:
                        c.check_blob(rel, data)
            else:
                c.tree()
        else:
            c.staged()
            if re.search(
                r"\bgit\b[^|;&]*\bcommit\b[^|;&]*\s-\w*a", cmd
            ):  # commit -a: unstaged tracked changes too
                c.tree()
        return 2 if c.report() else 0
    return 0


def main(argv):
    if "--hook-claude" in argv:
        return hook_claude()
    if "--version" in argv:
        print(VERSION)
        return 0
    repo = None
    strict = False
    mode = None
    paths = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--repo":
            repo = argv[i + 1]
            i += 1
        elif a in ("--staged", "--tree", "--push-range"):
            mode = a
        elif a == "--files":
            mode = a
            paths = argv[i + 1 :]
            break
        elif a == "--strict-home":
            strict = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        i += 1
    root = repo_root(repo or os.getcwd())
    if not root:
        print("leakcheck: not inside a git repository", file=sys.stderr)
        return 0
    own = [o.lower() for o in read_list("own-orgs.txt")]
    c = Checker(root, repo_tier(root, own), strict_home=strict)
    if mode == "--staged":
        c.staged()
    elif mode == "--push-range":
        c.push_range(sys.stdin.read().splitlines())
    elif mode == "--files":
        c.files(paths)
    else:
        c.tree()
    return c.report()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
