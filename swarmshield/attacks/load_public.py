"""Download (pinned versions) and read the public agent-attack task suites.

Only the attacker's wording is reused. The goal of every payload built from it is our own
(emit a canary token), so no public case is run as-is against anything. Real-looking emails and
URLs in the public text are replaced with `.test` addresses before anything is stored.
"""

import ast
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

RAW_DIR = Path("data/raw")

INJECAGENT_COMMIT = "f19c9f2c79a41046eb13c03c51a24c567a8ffa07"
AGENTDOJO_COMMIT = "089ed468cf3ed0322acc66b0211f26d9d90dbf60"
_IA = f"https://raw.githubusercontent.com/uiuc-kang-lab/InjecAgent/{INJECAGENT_COMMIT}/data"
_AD = (
    "https://raw.githubusercontent.com/ethz-spylab/agentdojo/"
    f"{AGENTDOJO_COMMIT}/src/agentdojo/default_suites/v1"
)
AGENTDOJO_SUITES = ("banking", "slack", "travel", "workspace")

# local name -> url
FILES = {
    "attacker_cases_dh.jsonl": f"{_IA}/attacker_cases_dh.jsonl",
    "attacker_cases_ds.jsonl": f"{_IA}/attacker_cases_ds.jsonl",
    **{f"agentdojo_{s}.py": f"{_AD}/{s}/injection_tasks.py" for s in AGENTDOJO_SUITES},
}

SOURCES = {
    "injecagent": {
        "name": "InjecAgent (attacker cases)",
        "url": "https://github.com/uiuc-kang-lab/InjecAgent",
        "commit": INJECAGENT_COMMIT,
        "licence": "MIT",
        "use": "attacker instruction wording only",
    },
    "agentdojo": {
        "name": "AgentDojo (v1 injection task goals)",
        "url": "https://github.com/ethz-spylab/agentdojo",
        "commit": AGENTDOJO_COMMIT,
        "licence": "MIT",
        "use": "attacker goal wording only; code, environments and tools are not used",
    },
}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"https?://\S+|www\.\S+")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(raw_dir: Path = RAW_DIR) -> dict[str, str]:
    """Fetch any missing file and return {name: sha256}. Existing files are not re-fetched."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        path = raw_dir / name
        if not path.exists():
            req = Request(url, headers={"User-Agent": "research-data-loader"})
            with urlopen(req, timeout=60) as resp:  # noqa: S310 - pinned https URLs above
                path.write_bytes(resp.read())
    return {name: sha256(raw_dir / name) for name in FILES}


def neutralise(text: str) -> str:
    """Replace real-looking emails and URLs so no payload can name a real person or site."""
    text = _EMAIL.sub("attacker@example.test", text)
    text = _URL.sub("https://attacker.example.test/", text)
    return re.sub(r"\s+", " ", text).strip().rstrip(".") + "."


def load_injecagent(raw_dir: Path = RAW_DIR) -> tuple[list[dict], dict]:
    """Unique attacker instructions from the direct-harm and data-stealing files."""
    out, stats, seen = [], {}, set()
    for kind in ("dh", "ds"):
        lines = (raw_dir / f"attacker_cases_{kind}.jsonl").read_text("utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
        kept = 0
        for row in rows:
            wording = neutralise(row["Attacker Instruction"])
            if wording in seen:
                continue
            seen.add(wording)
            out.append({"source": "injecagent", "wording": wording, "kind": kind})
            kept += 1
        stats[kind] = {"rows": len(rows), "kept": kept}
    return sorted(out, key=lambda r: r["wording"]), stats


def _goal_text(node: ast.expr) -> str | None:
    """Text of a string or f-string, with each {placeholder} shown as <resource>."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            v.value if isinstance(v, ast.Constant) else "<resource>" for v in node.values
        )
    return None


def load_agentdojo(raw_dir: Path = RAW_DIR) -> tuple[list[dict], dict]:
    """GOAL strings of the injection tasks, read with `ast` (the code is never imported)."""
    out, stats, seen = [], {}, set()
    for suite in AGENTDOJO_SUITES:
        tree = ast.parse((raw_dir / f"agentdojo_{suite}.py").read_text("utf-8"))
        found = kept = 0
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for stmt in cls.body:
                is_goal = isinstance(stmt, ast.Assign) and any(
                    getattr(t, "id", "") == "GOAL" for t in stmt.targets
                )
                if not is_goal:
                    continue
                found += 1
                text = _goal_text(stmt.value)
                if not text:
                    continue
                wording = neutralise(text.replace("<resource>", "the attacker resource"))
                if wording in seen:
                    continue
                seen.add(wording)
                out.append({"source": "agentdojo", "wording": wording, "kind": suite})
                kept += 1
        stats[suite] = {"goals": found, "kept": kept}
    return sorted(out, key=lambda r: r["wording"]), stats
