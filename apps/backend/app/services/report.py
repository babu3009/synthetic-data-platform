from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, Dict, List, Optional


def _try_render_fk_graph(schema: Dict[str, Any]) -> Optional[str]:
    """Return SVG text for FK graph if graphviz is available and schema contains fks."""
    try:
        from graphviz import Digraph  # type: ignore
    except Exception:
        return None

    tables = {t.get("name"): t for t in schema.get("tables", []) if isinstance(t, dict)}
    if not tables:
        return None
    g = Digraph(comment="FK Graph")
    for t in tables.keys():
        g.node(t)
    for tname, t in tables.items():
        for fk in t.get("fks", []) or []:
            to_table = fk.get("to_table")
            if to_table and to_table in tables:
                g.edge(tname, to_table)
    try:
        return g.pipe(format="svg").decode("utf-8")
    except Exception:
        return None


def _try_histogram_png(values: List[Any]) -> Optional[str]:
    """Return a base64 PNG histogram for numeric values using matplotlib, if available."""
    try:
        import matplotlib  # type: ignore
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    try:
        # Filter numeric values
        nums: List[float] = []
        for v in values:
            if isinstance(v, (int, float)):
                nums.append(float(v))
        if not nums:
            return None
        fig, ax = plt.subplots(figsize=(2.5, 1.2), dpi=120)
        ax.hist(nums, bins=10, color="#0d6efd")
        ax.set_yticks([])
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def create_html_report(
    *,
    request_id: str,
    target_dir: Path,
    schema: Optional[Dict[str, Any]] = None,
    summary: Optional[Dict[str, Any]] = None,
    artifacts: Optional[List[Dict[str, Any]]] = None,
    samples: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Path:
    """Create a self-contained HTML report and return its path.

    - schema: expected to include tables with fks for graph rendering
    - summary: overall counts, per-table counts, rule results, etc.
    - artifacts: list with {table, format, uri, size}
    - samples: optional small samples per table for histogram generation
    """

    fk_svg = _try_render_fk_graph(schema or {}) if schema else None
    # Build simple histograms from samples (first numeric column in each table)
    hist_images: Dict[str, str] = {}
    if samples:
        for tname, rows in samples.items():
            if not rows:
                continue
            # Collect first numeric-looking column values
            first_row = rows[0]
            for col, v in first_row.items():
                values = [r.get(col) for r in rows]
                img = _try_histogram_png(values) or ""
                if img:
                    hist_images[f"{tname}.{col}"] = img
                    break

    html = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8' />",
        "<meta name='viewport' content='width=device-width, initial-scale=1' />",
        "<title>Synthetic Data Report</title>",
        "<style>body{font-family:system-ui,Arial,sans-serif;margin:16px;}h1{font-size:20px;} .grid{display:grid;gap:12px} .card{border:1px solid #ddd;padding:12px;border-radius:8px;} .muted{color:#666;font-size:12px} img{max-width:100%}</style>",
        "</head>",
        "<body>",
        f"<h1>Validation Report &mdash; Request {request_id}</h1>",
        "<div class='grid'>",
    ]

    # Summary block
    if summary:
        html.append("<div class='card'><h2>Summary</h2><pre>")
        import json
        html.append(json.dumps(summary, indent=2))
        html.append("</pre></div>")

    # FK Graph
    if fk_svg:
        html.append("<div class='card'><h2>Foreign Key Graph</h2>")
        html.append(fk_svg)
        html.append("</div>")

    # Histograms
    if hist_images:
        html.append("<div class='card'><h2>Column Histograms (sampled)</h2>")
        for key, b64 in hist_images.items():
            html.append(f"<div><div class='muted'>{key}</div><img src='data:image/png;base64,{b64}' alt='hist {key}' /></div>")
        html.append("</div>")

    # Artifacts
    if artifacts:
        html.append("<div class='card'><h2>Artifacts</h2><ul>")
        for a in artifacts:
            label = f"{a.get('table') or ''} {a.get('format') or ''}"
            uri = a.get("uri", "#")
            size = a.get("size")
            size_str = f" ({size} bytes)" if isinstance(size, int) else ""
            html.append(f"<li><a href='{uri}'>{label}</a>{size_str}</li>")
        html.append("</ul></div>")

    html.append("</div></body></html>")

    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / "report.html"
    out.write_text("\n".join(html), encoding="utf-8")
    return out

__all__ = ["create_html_report"]
