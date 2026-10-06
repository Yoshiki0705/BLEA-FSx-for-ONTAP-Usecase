#!/usr/bin/env python3
"""Fail when source files carry an AWS account ID, a host IP address, or an email address.

The tracked rules are generic on purpose: this repository is public, so a detector that names the
real values it looks for publishes them. Real values (a specific account ID, a hostname, a name)
go in `.sensitive-patterns.private` at the repository root, one extended regular expression per
line, `#` for comments. That file is gitignored and read only when it exists; copy
`.sensitive-patterns.private.example` to start one.

Generic rules:
  account-id  any 12-digit number other than the documentation placeholder 123456789012
  ipv4        any IPv4 address outside the documentation ranges (RFC 5737), loopback, 0.0.0.0 and
              255.255.255.255. A network address written as a CIDR block with a prefix of /30 or
              shorter (a VPC CIDR) is a design parameter and is allowed; a host address is not
  email       any email address outside example.com / example.org / example.net and noreply

Findings print as `path:line: rule` without the matched text, so a real value is not copied into
a CI log.

    python3 tools/check_sensitive.py                 # usecases/ and shared/, *.ts
    python3 tools/check_sensitive.py FILE...         # the given files (pre-commit)
    python3 tools/check_sensitive.py --selftest      # every rule fires on its positive only
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_PATTERNS = REPO_ROOT / ".sensitive-patterns.private"
DEFAULT_ROOTS = ("usecases", "shared")
DEFAULT_SUFFIX = ".ts"
SKIP_DIRS = {"node_modules", "cdk.out", ".git"}

# Documentation placeholder. Add a publicly documented AWS-owned account ID here only together
# with the URL of the page that publishes it.
ALLOWED_ACCOUNT_IDS = {"123456789012"}

ACCOUNT_ID_RE = re.compile(r"(?<![0-9])[0-9]{12}(?![0-9])")
IPV4_RE = re.compile(
    r"(?<![0-9.])((?:[0-9]{1,3}\.){3}[0-9]{1,3})(?:/([0-9]{1,2}))?(?![0-9.])"
)
EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})"
)

DOC_NETWORKS = [
    ipaddress.ip_network(n)
    for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "127.0.0.0/8")
]
ALLOWED_IPS = {"0.0.0.0", "255.255.255.255"}
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net"}


def _ip_allowed(addr: str, prefix: str | None) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return True  # not an address (e.g. 999.1.1.1), nothing to leak
    if addr in ALLOWED_IPS or any(ip in net for net in DOC_NETWORKS):
        return True
    if prefix is not None and int(prefix) <= 30:
        try:
            ipaddress.ip_network(f"{addr}/{prefix}", strict=True)
            return True  # network address with host bits zero
        except ValueError:
            return False
    return False


def _email_allowed(match: re.Match[str]) -> bool:
    domain = match.group(1).lower()
    if domain in ALLOWED_EMAIL_DOMAINS or domain.endswith(".example"):
        return True
    return "noreply" in match.group(0).lower()


def load_local_patterns(path: Path = LOCAL_PATTERNS) -> list[re.Pattern[str]]:
    if not path.is_file():
        return []
    patterns = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            patterns.append(re.compile(line))
    return patterns


def scan_line(line: str, local: list[re.Pattern[str]]) -> list[str]:
    rules = []
    if any(m.group(0) not in ALLOWED_ACCOUNT_IDS for m in ACCOUNT_ID_RE.finditer(line)):
        rules.append("account-id")
    if any(not _ip_allowed(m.group(1), m.group(2)) for m in IPV4_RE.finditer(line)):
        rules.append("ipv4")
    if any(not _email_allowed(m) for m in EMAIL_RE.finditer(line)):
        rules.append("email")
    if any(p.search(line) for p in local):
        rules.append("local-pattern")
    return rules


def scan_file(path: Path, local: list[re.Pattern[str]]) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for rule in scan_line(line, local):
            findings.append(f"{path}:{lineno}: {rule}")
    return findings


def default_files() -> list[Path]:
    files = []
    for root in DEFAULT_ROOTS:
        base = REPO_ROOT / root
        for p in sorted(base.rglob(f"*{DEFAULT_SUFFIX}")):
            if p.is_file() and not SKIP_DIRS.intersection(
                p.relative_to(REPO_ROOT).parts
            ):
                files.append(p.relative_to(REPO_ROOT))
    return files


def selftest() -> int:
    # Synthetic fixtures for this detector; none belongs to any account, host, or person.
    cases = [
        ("account-id", "const a = '111122223333';", True),  # gitleaks:allow
        ("account-id", "const a = '123456789012';", False),
        ("account-id", "const big = 1234567890123;", False),  # 13 digits
        ("account-id", "ids: 123456789012,111122223333", True),  # gitleaks:allow
        ("ipv4", "host: '10.255.255.1'", True),  # gitleaks:allow
        ("ipv4", "host: '10.255.255.1/32'", True),  # gitleaks:allow
        ("ipv4", "vpcCidr: '10.0.0.0/16'", False),  # gitleaks:allow
        ("ipv4", "peer: '203.0.113.10'", False),
        ("ipv4", "any: '0.0.0.0/0'", False),
        ("ipv4", "version 1.2.3.4.5", False),
        ("email", "to: 'someone@mail.test.org'", True),  # gitleaks:allow
        ("email", "to: 'ops@example.com'", False),
        ("email", "to: '1+user@users.noreply.github.com'", False),
        ("email", "import { Stack } from '@aws-cdk/core';", False),
    ]
    failed = 0
    for rule, line, expect in cases:
        got = rule in scan_line(line, [])
        if got != expect:
            print(f"selftest FAIL: {rule} on {line!r}: expected {expect}, got {got}")
            failed += 1
    with tempfile.TemporaryDirectory() as tmp:
        pfile = Path(tmp) / "patterns"
        pfile.write_text("# comment\nsynthetic-secret-[0-9]+\n", encoding="utf-8")
        local = load_local_patterns(pfile)
        if "local-pattern" not in scan_line("x = 'synthetic-secret-42'", local):
            print("selftest FAIL: local pattern did not fire")
            failed += 1
        if load_local_patterns(Path(tmp) / "absent") != []:
            print("selftest FAIL: absent local file produced patterns")
            failed += 1
    if failed:
        return 1
    print(f"selftest OK ({len(cases) + 2} cases)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    local = load_local_patterns()
    files = args.paths or default_files()
    findings = [f for p in files for f in scan_file(p, local)]
    for f in findings:
        print(f)
    scope = f"{len(files)} files" + (
        f", {len(local)} local patterns" if local else ", no local patterns"
    )
    if findings:
        print(
            f"check_sensitive: {len(findings)} finding(s) in {scope}", file=sys.stderr
        )
        return 1
    print(f"check_sensitive: clean ({scope})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
