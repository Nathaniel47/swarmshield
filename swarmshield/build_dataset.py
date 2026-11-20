"""Build every dataset file and the data report: `python -m swarmshield.build_dataset`.

Outputs data/tasks.jsonl, data/payloads.jsonl, data/manifest.json and results/data_report.md.
Fails loudly on any quality problem listed in `validate`.
"""

import json
import random
import re
from collections import Counter
from pathlib import Path

from swarmshield.attacks.canary import PLACEHOLDER
from swarmshield.attacks.load_public import (
    RAW_DIR,
    SOURCES,
    download,
    load_agentdojo,
    load_injecagent,
)
from swarmshield.attacks.payloads import build_payloads
from swarmshield.tasks.generator import make_tasks

SEED = 42
N_TASKS = 60
DEV_SHARE = 0.3
DATA_DIR = Path("data")
REPORT = Path("results/data_report.md")


def split_groups(records: list[dict], key: str, strata, seed: int = SEED) -> None:
    """Add `split` (dev/test) in place: 30% of each stratum's groups go to dev, seeded.
    Records sharing `key` stay together so a paired payload never leaks across the split."""
    by_stratum: dict[str, list[str]] = {}
    for rec in records:
        groups = by_stratum.setdefault(strata(rec), [])
        if rec[key] not in groups:
            groups.append(rec[key])
    dev = set()
    for name in sorted(by_stratum):
        groups = sorted(by_stratum[name])
        random.Random(f"{seed}-{name}").shuffle(groups)
        dev.update(groups[: max(1, round(len(groups) * DEV_SHARE))])
    for rec in records:
        rec["split"] = "dev" if rec[key] in dev else "test"


def validate(tasks: list[dict], payloads: list[dict]) -> list[str]:
    problems = []
    for name, ids in (
        ("task_id", [t["task_id"] for t in tasks]),
        ("payload_id", [p["payload_id"] for p in payloads]),
        ("template", [p["template"] for p in payloads]),
    ):
        dupes = [k for k, n in Counter(ids).items() if n > 1]
        if dupes:
            problems.append(f"duplicate {name}: {dupes[:3]}")
    for p in payloads:
        if p["template"].count(PLACEHOLDER) != 1:
            problems.append(f"{p['payload_id']}: canary placeholder not exactly once")
        if re.search(r"[\w.+-]+@(?!example\.test)[\w.-]+\.\w+", p["template"]):
            problems.append(f"{p['payload_id']}: real-looking email")
        if re.search(r"https?://(?!attacker\.example\.test)", p["template"]):
            problems.append(f"{p['payload_id']}: real-looking URL")
    for t in tasks:
        text = " ".join(d["text"] for d in t["documents"])
        if len(set(t["required_facts"])) != len(t["required_facts"]):
            problems.append(f"{t['task_id']}: repeated required fact value")
        for fact in t["required_facts"]:
            if len(re.findall(rf"\b{re.escape(fact)}\b", text)) != 1:
                problems.append(f"{t['task_id']}: fact {fact} not exactly once in documents")
    return problems


def _table(counter: dict, header: str) -> str:
    rows = "\n".join(f"| {k} | {v} |" for k, v in sorted(counter.items()))
    return f"| {header} | count |\n|---|---|\n{rows}\n"


def write_report(tasks, payloads, stats, quality) -> str:
    by_split = Counter(p["split"] for p in payloads)
    cross = Counter(f"{p['attack']} / {p['source']} / {p['split']}" for p in payloads)
    docs = Counter(len(t["documents"]) for t in tasks)
    sample_task, sample_payload = tasks[0], next(p for p in payloads if p["source"] == "agentdojo")
    lines = [
        "# Data report",
        "",
        f"Seed {SEED}. Rebuild with `python -m swarmshield.build_dataset`.",
        "",
        "## Synthetic tasks",
        f"- {len(tasks)} tasks ({sum(t['split'] == 'dev' for t in tasks)} dev, "
        f"{sum(t['split'] == 'test' for t in tasks)} test).",
        f"- Documents per task: {dict(sorted(docs.items()))}.",
        "- Each required fact value appears exactly once in the task's documents (checked).",
        "",
        "```json",
        json.dumps(sample_task, indent=2),
        "```",
        "",
        "## Attack payloads",
        f"- {len(payloads)} payloads ({by_split['dev']} dev, {by_split['test']} test), "
        f"{len({p['group'] for p in payloads})} paired groups: each group has one prompt-infection "
        "and one memory-poisoning payload with the same wording, and stays in one split.",
        "",
        _table(Counter(p["attack"] for p in payloads), "attack"),
        _table(Counter(p["source"] for p in payloads), "source"),
        _table(cross, "attack / source / split"),
        "Sample payload (AgentDojo-derived, canary placeholder unfilled):",
        "",
        "```json",
        json.dumps(sample_payload, indent=2),
        "```",
        "",
        "## Public sources",
        f"- InjecAgent: {stats['injecagent']}",
        f"- AgentDojo: {stats['agentdojo']}",
        "",
        "## Quality problems found",
        *[f"- {q}" for q in quality],
        "",
    ]
    text = "\n".join(lines)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    return text


def build(raw_dir: Path = RAW_DIR, data_dir: Path = DATA_DIR) -> dict:
    hashes = download(raw_dir)
    ia, ia_stats = load_injecagent(raw_dir)
    ad, ad_stats = load_agentdojo(raw_dir)
    payloads = build_payloads(ia + ad, SEED)
    tasks = make_tasks(N_TASKS, SEED)
    for t in tasks:
        t["group"] = t["task_id"]
    split_groups(tasks, "group", lambda r: "tasks")
    split_groups(payloads, "group", lambda r: r["source"])
    problems = validate(tasks, payloads)
    if problems:
        raise SystemExit("data validation failed:\n" + "\n".join(problems))

    neutralised = sum("example.test" in w["wording"] for w in ia + ad)
    quality = [
        f"InjecAgent's two attacker files hold {ia_stats['dh']['rows'] + ia_stats['ds']['rows']} "
        f"rows and {len(ia)} unique instructions after neutralising emails and URLs. 30 are "
        "sampled (seeded) so the two public sources stay balanced.",
        "InjecAgent instructions target other applications (smart locks, banking, shopping "
        "accounts), so they are used as cover wording only. The checkable action is always the "
        "canary, never the original request.",
        f"{neutralised} public wordings contained a real-looking email or URL; these were "
        "replaced with attacker@example.test or https://attacker.example.test/ before storage.",
        "AgentDojo goals are read with `ast` from the pinned source files (code never imported). "
        "Placeholders for attacker resources (URLs, emails, IBANs) became 'the attacker resource' "
        "or `.test` addresses.",
        "Self-written payloads (6 per attack) are few and hand-picked, so the self source is "
        "small and its split has very few payloads; do not report per-source numbers on it alone.",
        "Synthetic facts are plain numbers in short sentences. A model can pass the fact check "
        "without reading carefully (for example by guessing a common year), a weakness of "
        "substring scoring that the evaluation will check with a no-document baseline.",
    ]
    stats = {"injecagent": ia_stats, "agentdojo": ad_stats}

    data_dir.mkdir(exist_ok=True)
    for name, rows in (("tasks", tasks), ("payloads", payloads)):
        with (data_dir / f"{name}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "seed": SEED,
        "sources": SOURCES,
        "raw_sha256": hashes,
        "counts": {"tasks": len(tasks), "payloads": len(payloads)},
    }
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")
    write_report(tasks, payloads, stats, quality)
    return manifest


if __name__ == "__main__":
    print(json.dumps(build()["counts"]))
