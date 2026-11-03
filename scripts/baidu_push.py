#!/usr/bin/env python3
"""Push every URL in the live sitemap to Baidu's webmaster push API (百度站长主动推送).

Baidu has no IndexNow: the普通收录 push API takes up to 2,000 URLs per call as a newline-
separated body against the token a verified property shows at ziyuan.baidu.com. The token is
per-site and private — pass it through the environment, never a flag (shells keep history):

    TREG_BAIDU_PUSH_TOKEN=xxxx uv run --frozen python scripts/baidu_push.py
    TREG_BAIDU_PUSH_TOKEN=xxxx uv run --frozen python scripts/baidu_push.py --base https://staging.example

Exit code is non-zero when Baidu rejects the batch (`success` < the URLs sent, or an HTTP error).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "http://data.zz.baidu.com/urls"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://treg.to")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    token = os.environ.get("TREG_BAIDU_PUSH_TOKEN", "")
    if not token and not args.dry_run:
        print("TREG_BAIDU_PUSH_TOKEN is not set (the property token from ziyuan.baidu.com)", file=sys.stderr)
        return 2

    with urllib.request.urlopen(f"{base}/sitemap.xml", timeout=30) as r:
        urls = re.findall(r"<loc>([^<]+)</loc>", r.read().decode())
    # The push API takes same-host URLs only; a stray alternate (hreflang mirror) would be refused.
    urls = [u for u in urls if u.startswith(base + "/") or u == base]
    print(f"{len(urls)} URLs in {base}/sitemap.xml")
    if not urls:
        return 2

    if args.dry_run:
        print("dry run — not submitting")
        return 0

    endpoint = f"{API}?site={urllib.parse.quote(base, safe='')}&token={urllib.parse.quote(token, safe='')}"
    body = "\n".join(urls).encode()
    req = urllib.request.Request(endpoint, data=body,
                                 headers={"Content-Type": "text/plain"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            reply = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Baidu rejected the batch: HTTP {e.code} {e.read().decode()[:200]}", file=sys.stderr)
        return 1
    # success / remain are Baidu's own quota bookkeeping; a refuse means the property or token is off.
    if int(reply.get("success", 0)) < len(urls):
        print(f"Baidu accepted {reply.get('success', 0)}/{len(urls)}: {reply}", file=sys.stderr)
        return 1
    print(f"Baidu: pushed {reply.get('success', 0)} URLs (remain {reply.get('remain', '?')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
