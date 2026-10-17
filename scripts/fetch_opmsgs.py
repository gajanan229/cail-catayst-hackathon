"""Fetch HPE operator messages; merge without breaking the simulator's Appendix A templates.

Run with --offline to use var/opmsgs_cache/ch{chapter}.html exclusively. The
manual's omm.message/cause/effect/recovery comments delimit records; replaceable
HTML spans become named template slots. No third-party HTML parser is needed.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://ftp.hp.com/pub/softlib/NonStopOpMsgsMnl/"
CHAPTERS = {68: "OMF", 78: "PATHWAY", 15: "COM-KRNL", 121: "TMF"}


def plain(value: str) -> str:
    value = re.sub(r"</?(?:p|div|li|br|tr)\b[^>]*>", " ", value)
    value = re.sub(r"<[^>]*>", "", value)
    return " ".join(html.unescape(value).split())


def slot(match: re.Match) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", plain(match[1]).lower()).strip("_")
    return "{" + name + "}"


def parse_chapter(raw: bytes, chapter: int) -> list[dict]:
    # The source declares ISO-8859-1 (including literal accented characters).
    source = raw.decode("iso-8859-1")
    records = []
    blocks = re.finditer(
        r'<!--omm.message key="[^/]+/([^/]+)/[^/]+/[^/]+/(-?\d+)"-->(.*?)<!--/omm.message-->',
        source, re.S,
    )
    for block in blocks:
        subsystem, number, body = block[1], int(block[2]), block[3]
        # The first paragraph contains the entire message, including nested tt tags.
        message = re.search(r'<p>\s*<tt class="computeroutput">(.*?)</p>', body, re.S)
        if not message:
            continue
        marked = re.sub(r'<i class="replaceable">(.*?)</i>', slot, message[1], flags=re.S)
        template = plain(marked)
        explanations = {}
        for field in ("cause", "effect", "recovery"):
            match = re.search(rf"<!--omm.{field}-->(.*?)<!--/omm.{field}-->", body, re.S)
            explanations[field] = plain(match[1]) if match else ""
        if not template or not all(explanations.values()):
            continue  # Never manufacture explanations for an unrecognized layout.
        records.append({
            "id": f"opmsg:{subsystem}:{number}", "doc_type": "operator_message",
            "subsystem": subsystem, "number": number, "text_template": template,
            "variables": list(dict.fromkeys(re.findall(r"\{([a-z0-9_]+)\}", template))),
            **explanations, "critical": False, "severity_hint": 2,
            "real": True, "source": BASE + f"ch{chapter:02}.html", "status": "active",
        })
    return records


def load_chapter(chapter: int, cache: Path, offline: bool, refresh: bool) -> bytes | None:
    path = cache / f"ch{chapter:02}.html"
    if path.exists() and not refresh:
        print(f"ch{chapter}: cache ({path.stat().st_size} bytes)")
        return path.read_bytes()
    if not offline:
        try:
            request = urllib.request.Request(BASE + path.name, headers={"User-Agent": "Baton-manual-fetcher/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
            if b"<!--omm.message" not in raw:
                raise ValueError("response has no manual message markers")
            cache.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            print(f"ch{chapter}: fetched {len(raw)} bytes")
            return raw
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"ch{chapter}: unavailable: {exc}; retaining existing records", file=sys.stderr)
    if path.exists():
        print(f"ch{chapter}: using cached fallback")
        return path.read_bytes()
    print(f"ch{chapter}: no cache; retaining Appendix A fallback", file=sys.stderr)
    return None


def merge(existing: list[dict], chapters: list[list[dict]], rules: list[dict], limit: int) -> list[dict]:
    records = {record["id"]: dict(record) for record in existing}
    protected = {(m["subsystem"], m["number"]): m for m in rules}
    # Update existing records first, so limits never omit a simulator explanation.
    for record in (r for chapter in chapters for r in chapter):
        if record["id"] not in records:
            continue
        old = records[record["id"]]
        rule = protected.get((record["subsystem"], record["number"]))
        if rule:
            old.update({key: record[key] for key in ("cause", "effect", "recovery", "source")})
        else:
            records[record["id"]] = dict(record)
    # Round-robin selection keeps both chapters represented within the MVP budget.
    for i in range(max(map(len, chapters), default=0)):
        for chapter in chapters:
            if i < len(chapter) and len(records) < limit:
                records.setdefault(chapter[i]["id"], chapter[i])
    for key, rule in protected.items():
        matches = [r for r in records.values() if (r["subsystem"], r["number"]) == key]
        if not matches:
            raise ValueError(f"simulator message {key} missing from existing pack")
        if rule.get("real"):
            for record in matches:
                record.update(text_template=rule["template"], critical=rule["critical"],
                              severity_hint=rule["severity_hint"])
                record["variables"] = list(dict.fromkeys(re.findall(r"\{([a-z_]+)\}", rule["template"])))
                record["synthetic"] = True
                record["synthetic_note"] = (
                    "Appendix A simulator template (state words/layout may be simulated); "
                    "cause/effect/recovery from the manual when cached, otherwise synthetic fallback."
                )
    return sorted(records.values(), key=lambda r: (r["subsystem"], r["number"], r["id"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="try network before cached fallback")
    parser.add_argument("--chapters", nargs="+", type=int, choices=CHAPTERS, default=[68, 78])
    parser.add_argument("--limit", type=int, default=150, help="maximum merged records; existing records are never removed")
    args = parser.parse_args()
    if args.offline and args.refresh:
        parser.error("--offline and --refresh are mutually exclusive")
    import yaml  # Already a pinned backend dependency; only needed for simulator templates.

    path = ROOT / "data/content/operator_messages.jsonl"
    existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rules = yaml.safe_load((ROOT / "data/rules/ems_messages.yaml").read_text(encoding="utf-8"))["messages"]
    chapters = []
    for chapter in args.chapters:
        raw = load_chapter(chapter, ROOT / "var/opmsgs_cache", args.offline, args.refresh)
        parsed = parse_chapter(raw, chapter) if raw else []
        print(f"ch{chapter}: parsed {len(parsed)} complete records")
        chapters.append(parsed)
    records = merge(existing, chapters, rules, args.limit)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    manifest_path = ROOT / "data/content/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["counts"]["operator_messages"] = len(records)
    manifest["operator_message_mode"] = (
        "HPE manual selection with Appendix A simulator templates preserved; "
        "raw HTML cached locally, synthetic APP chatter retained"
        if any(chapters) else "Appendix A fallback; manual unavailable and no usable cache"
    )
    manifest["operator_message_chapters"] = [c for c, records_ in zip(args.chapters, chapters) if records_]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Merged {len(existing)} -> {len(records)} records: {dict(Counter(r['subsystem'] for r in records))}")
    print(f"Real: {sum(bool(r.get('real')) for r in records)}; synthetic templates/chatter: "
          f"{sum(bool(r.get('synthetic')) for r in records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
