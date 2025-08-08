#!/usr/bin/env python3
"""Generate a data flow diagram (docs/dfd.png) from the run_pipeline function.

If Graphviz is available it is used for rendering, otherwise a simple PNG
renderer implemented with the Python standard library is used.
"""
from __future__ import annotations

import importlib.util
import inspect
import re
from pathlib import Path
from typing import List, Optional, Tuple

try:  # Graphviz is optional in restricted environments
    from graphviz import Digraph
    from graphviz.backend import ExecutableNotFound
except Exception:  # pragma: no cover - fallback when graphviz is missing
    Digraph = None  # type: ignore
    ExecutableNotFound = Exception  # type: ignore

SCRIPT_DIR = Path(__file__).resolve().parent
MAIN_PATH = SCRIPT_DIR / "main.py"


def _load_run_pipeline():
    spec = importlib.util.spec_from_file_location("_main", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module.run_pipeline


def extract_steps() -> Tuple[List[str], List[Tuple[str, str]]]:
    """Extract pipeline step names and their connections.

    Returns
    -------
    Tuple[List[str], List[Tuple[str, str]]]
        A tuple containing the list of step names and the list of edges
        representing the data flow between steps.
    """

    run_pipeline = _load_run_pipeline()
    source = inspect.getsource(run_pipeline)
    patterns = [
        (r"DataLoader\(", "Load requirements"),
        (r"LLMInterface\(", "Generate OWL"),
        (r"OntologyBuilder\(", "Build ontology"),
        (r"run_reasoner", "Run reasoner"),
        (r"SHACLValidator\(", "Validate SHACL"),
        (r"RepairLoop\(", "Repair loop"),
    ]
    steps: List[str] = []
    for line in source.splitlines():
        for pattern, label in patterns:
            if re.search(pattern, line) and label not in steps:
                steps.append(label)

    edges: List[Tuple[str, str]] = []
    previous = "Inputs"
    for step in steps:
        edges.append((previous, step))
        previous = step
    edges.append((previous, "Outputs"))

    if "Repair loop" in steps and "Validate SHACL" in steps:
        edges.append(("Repair loop", "Validate SHACL"))

    return steps, edges


def build_graphviz(steps: List[str], edges: List[Tuple[str, str]]) -> Optional[Digraph]:
    if Digraph is None:
        return None
    dot = Digraph("DFD", format="png")
    dot.attr(rankdir="LR")

    for node in ["Inputs", *steps, "Outputs"]:
        dot.node(node)

    for start, end in edges:
        dot.edge(start, end)

    return dot


FONT = {
    "A": ["01110","10001","10001","11111","10001","10001","10001"],
    "B": ["11110","10001","10001","11110","10001","10001","11110"],
    "C": ["01111","10000","10000","10000","10000","10000","01111"],
    "D": ["11110","10001","10001","10001","10001","10001","11110"],
    "E": ["11111","10000","10000","11110","10000","10000","11111"],
    "F": ["11111","10000","10000","11110","10000","10000","10000"],
    "G": ["01111","10000","10000","10111","10001","10001","01110"],
    "H": ["10001","10001","10001","11111","10001","10001","10001"],
    "I": ["01110","00100","00100","00100","00100","00100","01110"],
    "J": ["00111","00010","00010","00010","10010","10010","01100"],
    "K": ["10001","10010","10100","11000","10100","10010","10001"],
    "L": ["10000","10000","10000","10000","10000","10000","11111"],
    "M": ["10001","11011","10101","10101","10001","10001","10001"],
    "N": ["10001","11001","10101","10011","10001","10001","10001"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "P": ["11110","10001","10001","11110","10000","10000","10000"],
    "Q": ["01110","10001","10001","10001","10101","10010","01101"],
    "R": ["11110","10001","10001","11110","10100","10010","10001"],
    "S": ["01111","10000","10000","01110","00001","00001","11110"],
    "T": ["11111","00100","00100","00100","00100","00100","00100"],
    "U": ["10001","10001","10001","10001","10001","10001","01110"],
    "V": ["10001","10001","10001","10001","10001","01010","00100"],
    "W": ["10001","10001","10001","10101","10101","10101","01010"],
    "X": ["10001","10001","01010","00100","01010","10001","10001"],
    "Y": ["10001","10001","01010","00100","00100","00100","00100"],
    "Z": ["11111","00001","00010","00100","01000","10000","11111"],
    " ": ["00000","00000","00000","00000","00000","00000","00000"],
}


def render_png(
    steps: List[str], edges: List[Tuple[str, str]], out_file: Path
) -> None:
    """Render a simple PNG representation of the data flow diagram.

    Parameters
    ----------
    steps:
        Ordered list of step names appearing in the pipeline.
    edges:
        Arbitrary connections between nodes. This allows rendering
        of cycles such as the Repair loop returning to SHACL
        validation.
    out_file:
        Path where the generated PNG should be written.
    """

    width = 140 * (len(steps) + 2)
    # Extra height to provide room for return arrows above the nodes
    height = 140
    white = (255, 255, 255)
    black = (0, 0, 0)
    canvas = [[white for _ in range(width)] for _ in range(height)]

    def draw_rect(x1: int, y1: int, x2: int, y2: int) -> None:
        for x in range(x1, x2 + 1):
            canvas[y1][x] = black
            canvas[y2][x] = black
        for y in range(y1, y2 + 1):
            canvas[y][x1] = black
            canvas[y][x2] = black

    def draw_hline(x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            canvas[y][x] = black

    def draw_vline(x: int, y1: int, y2: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            canvas[y][x] = black

    def draw_arrow_right(x: int, y: int) -> None:
        for i in range(5):
            canvas[y - i][x - i] = black
            canvas[y + i][x - i] = black

    def draw_text(x: int, y: int, text: str) -> None:
        for char in text.upper():
            glyph = FONT.get(char, FONT[" "])
            for row_idx, row in enumerate(glyph):
                for col_idx, bit in enumerate(row):
                    if bit == "1":
                        canvas[y + row_idx][x + col_idx] = black
            x += 6

    def draw_forward_edge(start: Tuple[int, int], end: Tuple[int, int]) -> None:
        sx, sy = start
        ex, ey = end
        draw_hline(sx, ex - 20, sy)
        draw_arrow_right(ex - 20, ey)

    def draw_return_edge(start: Tuple[int, int], end: Tuple[int, int]) -> None:
        sx, sy = start
        ex, ey = end
        top = sy - 40
        draw_vline(sx, sy, top)
        draw_hline(sx, ex - 20, top)
        draw_vline(ex - 20, top, ey)
        draw_arrow_right(ex - 20, ey)

    # --- draw nodes -----------------------------------------------------
    x = 20
    box_top = height // 2 - 20
    centers: dict[str, Tuple[int, int]] = {}
    draw_rect(x, box_top, x + 100, box_top + 40)
    draw_text(x + 10, box_top + 10, "INPUTS")
    centers["Inputs"] = (x + 50, box_top + 20)
    x += 140
    for step in steps:
        draw_rect(x, box_top, x + 100, box_top + 40)
        draw_text(x + 10, box_top + 10, step.upper())
        centers[step] = (x + 50, box_top + 20)
        x += 140
    draw_rect(x, box_top, x + 100, box_top + 40)
    draw_text(x + 10, box_top + 10, "OUTPUTS")
    centers["Outputs"] = (x + 50, box_top + 20)

    # --- draw edges -----------------------------------------------------
    for start, end in edges:
        if start not in centers or end not in centers:
            continue
        if centers[start][0] <= centers[end][0]:
            draw_forward_edge(centers[start], centers[end])
        else:
            draw_return_edge(centers[start], centers[end])

    import zlib, struct

    raw = b""
    for row in canvas:
        raw += b"\x00"
        for r, g, b in row:
            raw += bytes([r, g, b])
    compressed = zlib.compress(raw)

    def chunk(tag, data):
        return (len(data).to_bytes(4, "big") + tag + data +
                zlib.crc32(tag + data).to_bytes(4, "big"))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", (width).to_bytes(4, "big") + (height).to_bytes(4, "big") + bytes([8,2,0,0,0]))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    out_file.write_bytes(png)


def main(out_file: str = "docs/dfd.png") -> None:
    steps, edges = extract_steps()
    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    graph = build_graphviz(steps, edges)
    if graph is not None:
        try:
            graph.render(out_path.with_suffix(""), cleanup=True)
            return
        except ExecutableNotFound:
            pass
    render_png(steps, edges, out_path)


if __name__ == "__main__":
    main()