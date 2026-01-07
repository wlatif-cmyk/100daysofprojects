#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import datetime as dt
import html
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from hashlib import sha1
from pathlib import Path
from typing import Dict, List, Tuple, Optional

DEFAULT_IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode",
    "node_modules", "dist", "build", "__pycache__",
    ".venv", "venv", ".mypy_cache", ".pytest_cache",
    ".next", ".cache", "out", "target",
}

CODE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".c", ".h", ".cpp", ".hpp",
    ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".scala", ".lua", ".sh", ".ps1",
    ".sql", ".html", ".css", ".yaml", ".yml", ".json", ".toml", ".ini", ".md"
}

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".mp4", ".mov", ".avi", ".mkv", ".bin"
}

COMMENT_PREFIX = {
    ".py": "#",
    ".sh": "#",
    ".ps1": "#",
    ".rb": "#",
    ".php": "//",
    ".js": "//",
    ".ts": "//",
    ".java": "//",
    ".kt": "//",
    ".c": "//",
    ".h": "//",
    ".cpp": "//",
    ".hpp": "//",
    ".cs": "//",
    ".go": "//",
    ".rs": "//",
    ".swift": "//",
    ".scala": "//",
    ".lua": "--",
    ".sql": "--",
    ".yaml": "#",
    ".yml": "#",
    ".toml": "#",
    ".ini": ";",
}

@dataclass
class FileStats:
    path: str
    ext: str
    bytes: int
    lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    sha1: str

@dataclass
class PyFuncStats:
    name: str
    lineno: int
    end_lineno: int
    lines: int
    approx_complexity: int
    file: str

@dataclass
class Report:
    project_path: str
    created_at: str
    totals: Dict[str, int]
    by_ext: Dict[str, Dict[str, int]]
    largest_files: List[Dict]
    duplicate_blocks: List[Dict]
    python_functions: List[Dict]
    score: int
    insights: List[str]
    tech_summary: List[str]
    next_actions: List[str]

def is_probably_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTS:
        return True
    try:
        with path.open("rb") as f:
            chunk = f.read(2048)
        return b"\x00" in chunk
    except Exception:
        return True

def safe_read_text(path: Path, max_bytes: int) -> Optional[str]:
    try:
        if path.stat().st_size > max_bytes:
            return None
        data = path.read_bytes()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="replace")
    except Exception:
        return None

def normalize_for_dupe(line: str) -> str:
    line = re.sub(r"//.*$", "", line)
    line = re.sub(r"#.*$", "", line)
    line = re.sub(r"/\*.*?\*/", "", line)
    line = line.strip()
    return re.sub(r"\s+", " ", line)

def approx_complexity_from_ast(node: ast.AST) -> int:
    branchers = (
        ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BoolOp,
        ast.IfExp, ast.Match, ast.ExceptHandler
    )
    count = 1
    for n in ast.walk(node):
        if isinstance(n, branchers):
            count += 1
    return count

def collect_files(root: Path, ignore_dirs: set, max_files: int) -> List[Path]:
    found: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for fn in filenames:
            p = Path(dirpath) / fn
            if len(found) >= max_files:
                return found
            if p.suffix.lower() in CODE_EXTS or (p.suffix == "" and p.stat().st_size < 200_000):
                found.append(p)
    return found

def analyze_files(paths: List[Path], max_file_bytes: int) -> Tuple[List[FileStats], Dict[str, str]]:
    file_stats: List[FileStats] = []
    texts: Dict[str, str] = {}
    for p in paths:
        if is_probably_binary(p):
            continue
        txt = safe_read_text(p, max_file_bytes)
        if txt is None:
            continue

        ext = p.suffix.lower() or "(none)"
        prefix = COMMENT_PREFIX.get(p.suffix.lower())
        lines = txt.splitlines()
        blank = sum(1 for l in lines if not l.strip())
        comment = 0
        code = 0
        for l in lines:
            s = l.strip()
            if not s:
                continue
            if prefix and s.startswith(prefix):
                comment += 1
            else:
                code += 1

        h = sha1(txt.encode("utf-8", errors="ignore")).hexdigest()
        fs = FileStats(
            path=str(p),
            ext=ext,
            bytes=len(txt.encode("utf-8", errors="ignore")),
            lines=len(lines),
            code_lines=code,
            comment_lines=comment,
            blank_lines=blank,
            sha1=h,
        )
        file_stats.append(fs)
        texts[str(p)] = txt
    return file_stats, texts

def find_duplicate_blocks(texts: Dict[str, str], min_block_lines: int = 12) -> List[Dict]:
    block_map: Dict[str, List[Tuple[str, int]]] = {}
    for file_path, txt in texts.items():
        lines = txt.splitlines()
        if len(lines) < min_block_lines:
            continue
        norm = [normalize_for_dupe(l) for l in lines]
        step = 2
        for i in range(0, len(norm) - min_block_lines + 1, step):
            block = "\n".join(norm[i:i + min_block_lines]).strip()
            if not block or block.count("\n") < min_block_lines - 1:
                continue
            if sum(1 for l in block.splitlines() if l.strip()) < int(min_block_lines * 0.7):
                continue
            bh = sha1(block.encode("utf-8")).hexdigest()
            block_map.setdefault(bh, []).append((file_path, i + 1))

    dups: List[Dict] = []
    for bh, hits in block_map.items():
        if len(hits) >= 2:
            dups.append({
                "hash": bh,
                "occurrences": [{"file": f, "start_line": ln} for f, ln in hits[:10]],
                "count": len(hits),
                "block_lines": min_block_lines
            })

    dups.sort(key=lambda x: x["count"], reverse=True)
    return dups[:25]

def analyze_python_functions(texts: Dict[str, str]) -> List[PyFuncStats]:
    funcs: List[PyFuncStats] = []
    for file_path, txt in texts.items():
        if not file_path.lower().endswith(".py"):
            continue
        try:
            tree = ast.parse(txt)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", None)
                if end is None:
                    continue
                start = getattr(node, "lineno", 1)
                lines = max(1, end - start + 1)
                comp = approx_complexity_from_ast(node)
                funcs.append(PyFuncStats(
                    name=node.name,
                    lineno=start,
                    end_lineno=end,
                    lines=lines,
                    approx_complexity=comp,
                    file=file_path
                ))
    funcs.sort(key=lambda f: (f.lines, f.approx_complexity), reverse=True)
    return funcs[:50]

def build_metrics(files: List[FileStats]) -> Tuple[Dict[str, int], Dict[str, Dict[str, int]]]:
    totals = {
        "files": len(files),
        "bytes": sum(f.bytes for f in files),
        "lines": sum(f.lines for f in files),
        "code_lines": sum(f.code_lines for f in files),
        "comment_lines": sum(f.comment_lines for f in files),
        "blank_lines": sum(f.blank_lines for f in files),
    }
    by_ext: Dict[str, Dict[str, int]] = {}
    for f in files:
        d = by_ext.setdefault(f.ext, {"files": 0, "lines": 0, "code_lines": 0, "comment_lines": 0, "bytes": 0})
        d["files"] += 1
        d["lines"] += f.lines
        d["code_lines"] += f.code_lines
        d["comment_lines"] += f.comment_lines
        d["bytes"] += f.bytes
    return totals, by_ext

def score_and_insights(
    totals: Dict[str, int],
    files: List[FileStats],
    py_funcs: List[PyFuncStats],
    dup_blocks: List[Dict]
) -> Tuple[int, List[str], List[str], List[str]]:

    lines = totals["lines"]
    code_lines = totals["code_lines"]
    comment_lines = totals["comment_lines"]
    files_count = totals["files"]

    comment_ratio = (comment_lines / max(1, code_lines))
    avg_file_lines = (lines / max(1, files_count))

    largest = sorted(files, key=lambda f: f.lines, reverse=True)[:5]
    largest_lines = largest[0].lines if largest else 0

    long_funcs = [f for f in py_funcs if f.lines >= 60]
    gnarly_funcs = [f for f in py_funcs if f.approx_complexity >= 12]
    max_func_lines = max((f.lines for f in py_funcs), default=0)
    max_complexity = max((f.approx_complexity for f in py_funcs), default=0)

    dupe_hits = sum(d["count"] for d in dup_blocks[:5])

    score = 100
    if lines > 8000: score -= 10
    if lines > 20000: score -= 10

    if comment_ratio < 0.06: score -= 10
    if comment_ratio < 0.03: score -= 10

    if avg_file_lines > 250: score -= 8
    if largest_lines > 800: score -= 10
    if largest_lines > 1500: score -= 10

    if len(long_funcs) >= 3: score -= 8
    if len(gnarly_funcs) >= 3: score -= 8

    if dupe_hits >= 8: score -= 8
    if dupe_hits >= 20: score -= 8

    score = max(5, min(100, score))

    tech: List[str] = []
    tech.append(f"Scanned {files_count} files: {lines:,} total lines ({code_lines:,} code, {comment_lines:,} comments).")
    tech.append(f"Comment-to-code ratio: {comment_ratio:.2%}. Average file size: {avg_file_lines:.1f} lines.")
    if largest:
        tech.append(f"Largest file: {Path(largest[0].path).name} at {largest[0].lines} lines.")
    if py_funcs:
        tech.append(f"Python functions analyzed: {len(py_funcs)} (max func length: {max_func_lines}, max complexity: {max_complexity}).")
    if dup_blocks:
        tech.append(f"Potential duplicate blocks found: {len(dup_blocks)} (top block repeats: {dup_blocks[0]['count']}).")

    insights: List[str] = []
    next_actions: List[str] = []

    if comment_ratio < 0.03:
        insights.append("Documentation coverage looks low (very low comment-to-code ratio).")
        next_actions.append("Add docstrings to public functions and a short header comment for non-obvious modules.")
    elif comment_ratio < 0.06:
        insights.append("Documentation coverage is on the low side.")
        next_actions.append("Add concise docstrings for key functions and clarify any tricky logic branches.")

    if largest_lines > 1500:
        insights.append("One or more files are extremely large, which can slow down navigation and refactoring.")
        next_actions.append("Split the largest file into smaller modules (e.g., core/, ui/, services/, utils/).")
    elif largest_lines > 800:
        insights.append("At least one file is quite large, which can make changes riskier.")
        next_actions.append("Extract helpers/constants into separate files and group related functions into modules.")

    if avg_file_lines > 250:
        insights.append("Average file size is high, which often correlates with mixed responsibilities per file.")
        next_actions.append("Enforce a soft file-size cap (200–300 lines) and modularize by feature.")

    if len(long_funcs) >= 3:
        insights.append("There are multiple long functions (60+ lines), which can reduce readability and testability.")
        next_actions.append("Refactor long functions into smaller helpers with single responsibilities and clearer naming.")

    if len(gnarly_funcs) >= 3:
        insights.append("Several Python functions show high branching/complexity, which increases bug risk.")
        next_actions.append("Flatten nested conditionals, use early returns, and split logic into pure functions where possible.")

    if dupe_hits >= 20:
        insights.append("High duplication detected across the codebase (copy/paste patterns).")
        next_actions.append("Extract repeated blocks into shared helpers/classes and delete duplicates.")
    elif dupe_hits >= 8:
        insights.append("Moderate duplication detected across multiple files.")
        next_actions.append("Search repeated patterns and centralize them into reusable utilities.")

    if not insights:
        insights.append("No major red flags detected from the heuristics used here.")
        next_actions.append("Add basic tests + a small CI check (lint/typecheck) for a big quality jump.")

    if score < 70:
        next_actions.append("Quick win: run a formatter (black/prettier) + add a linter (ruff/eslint) and fix top warnings.")
    if score < 55:
        next_actions.append("Add a /docs or README section describing how to run the project + project structure.")

    return score, insights[:12], tech[:12], next_actions[:12]

def render_html(report: Report) -> str:
    r = report
    totals = r.totals
    by_ext_sorted = sorted(r.by_ext.items(), key=lambda kv: (kv[1]["lines"], kv[1]["files"]), reverse=True)

    def fmt_bytes(n: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if n < 1024:
                return f"{n:.0f}{unit}"
            n /= 1024
        return f"{n:.1f}TB"

    def li(items: List[str]) -> str:
        return "\n".join(f"<li>{html.escape(x)}</li>" for x in items)

    largest_rows = "\n".join(
        f"<tr><td>{html.escape(x['name'])}</td><td>{x['lines']}</td><td>{fmt_bytes(x['bytes'])}</td></tr>"
        for x in r.largest_files
    )

    ext_rows = "\n".join(
        f"<tr><td>{html.escape(ext)}</td><td>{d['files']}</td><td>{d['lines']}</td><td>{d['code_lines']}</td><td>{d['comment_lines']}</td></tr>"
        for ext, d in by_ext_sorted[:20]
    )

    func_rows = "\n".join(
        f"<tr><td>{html.escape(f['name'])}</td><td>{f['lines']}</td><td>{f['approx_complexity']}</td><td>{html.escape(Path(f['file']).name)}</td><td>{f['lineno']}-{f['end_lineno']}</td></tr>"
        for f in r.python_functions[:25]
    ) or "<tr><td colspan='5'>No Python functions analyzed.</td></tr>"

    dupe_rows = "\n".join(
        f"<tr><td>{d['count']}</td><td>{d['block_lines']}</td><td>{html.escape(d['occurrences'][0]['file'])}</td></tr>"
        for d in r.duplicate_blocks[:15]
    ) or "<tr><td colspan='3'>No duplicate blocks detected (or none above threshold).</td></tr>"

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Codebase Insight Report</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; line-height: 1.35; }}
    .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 16px; margin: 14px 0; }}
    .score {{ font-size: 44px; font-weight: 800; }}
    .muted {{ color: #666; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #eee; padding: 8px; text-align: left; font-size: 14px; }}
    th {{ background: #fafafa; }}
    code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>📌 Codebase Insight Report</h1>
  <div class="muted">
    Project: <code>{html.escape(r.project_path)}</code><br/>
    Generated: {html.escape(r.created_at)}
  </div>

  <div class="card">
    <div class="score">Score: {r.score}/100</div>
    <h3>Insights</h3>
    <ul>{li(r.insights)}</ul>
  </div>

  <div class="card">
    <h3>Next Actions</h3>
    <ul>{li(r.next_actions)}</ul>
  </div>

  <div class="card">
    <h3>Technical Summary</h3>
    <ul>{li(r.tech_summary)}</ul>
  </div>

  <div class="card">
    <h3>Totals</h3>
    <ul>
      <li>Files: {totals["files"]}</li>
      <li>Total lines: {totals["lines"]:,}</li>
      <li>Code lines: {totals["code_lines"]:,}</li>
      <li>Comment lines: {totals["comment_lines"]:,}</li>
      <li>Blank lines: {totals["blank_lines"]:,}</li>
      <li>Total size: {fmt_bytes(totals["bytes"])}</li>
    </ul>
  </div>

  <div class="card">
    <h3>Top Extensions</h3>
    <table>
      <thead><tr><th>Ext</th><th>Files</th><th>Lines</th><th>Code</th><th>Comments</th></tr></thead>
      <tbody>
        {ext_rows}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h3>Largest Files</h3>
    <table>
      <thead><tr><th>File</th><th>Lines</th><th>Size</th></tr></thead>
      <tbody>
        {largest_rows}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h3>Python Function Offenders</h3>
    <table>
      <thead><tr><th>Function</th><th>Lines</th><th>Complexity</th><th>File</th><th>Range</th></tr></thead>
      <tbody>
        {func_rows}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h3>Duplicate Blocks (Heuristic)</h3>
    <table>
      <thead><tr><th>Repeats</th><th>Block lines</th><th>Example file</th></tr></thead>
      <tbody>
        {dupe_rows}
      </tbody>
    </table>
    <div class="muted">Duplicates are estimated using normalized line blocks; false positives are possible.</div>
  </div>
</body>
</html>
"""

def main():
    ap = argparse.ArgumentParser(description="Generate a codebase insight report (JSON + HTML).")
    ap.add_argument("path", nargs="?", default=".", help="Project folder to scan")
    ap.add_argument("--out", default="code_insight_out", help="Output folder")
    ap.add_argument("--max-files", type=int, default=3000, help="Max files to consider")
    ap.add_argument("--max-mb", type=int, default=20, help="Max size per file to read (MB)")
    ap.add_argument("--min-dupe-lines", type=int, default=12, help="Minimum lines in a duplicate block")
    ap.add_argument("--ignore", nargs="*", default=[], help="Extra directory names to ignore")
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.exists() or not root.is_dir():
        print(f"Path not found or not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ignore_dirs = set(DEFAULT_IGNORE_DIRS) | set(args.ignore)

    files = collect_files(root, ignore_dirs, args.max_files)
    file_stats, texts = analyze_files(files, max_file_bytes=args.max_mb * 1024 * 1024)

    totals, by_ext = build_metrics(file_stats)

    dup_blocks = find_duplicate_blocks(texts, min_block_lines=args.min_dupe_lines)
    py_funcs = analyze_python_functions(texts)

    score, insights, tech, actions = score_and_insights(totals, file_stats, py_funcs, dup_blocks)

    largest_files = sorted(file_stats, key=lambda f: f.lines, reverse=True)[:10]
    largest_payload = [{
        "name": Path(f.path).name,
        "path": f.path,
        "lines": f.lines,
        "bytes": f.bytes
    } for f in largest_files]

    report = Report(
        project_path=str(root),
        created_at=dt.datetime.now().isoformat(timespec="seconds"),
        totals=totals,
        by_ext=by_ext,
        largest_files=largest_payload,
        duplicate_blocks=dup_blocks,
        python_functions=[asdict(f) for f in py_funcs],
        score=score,
        insights=insights,
        tech_summary=tech,
        next_actions=actions
    )

    json_path = out_dir / "report.json"
    html_path = out_dir / "report.html"

    json_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")

    print("\n✅ Done.")
    print(f"Score: {score}/100")
    print("Top insights:")
    for x in insights[:5]:
        print(f" - {x}")
    print("\nNext actions:")
    for x in actions[:5]:
        print(f" - {x}")
    print("\nOutput:")
    print(f"  - {json_path}")
    print(f"  - {html_path}\n")

if __name__ == "__main__":
    main()
