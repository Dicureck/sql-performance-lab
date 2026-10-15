"""Generate an SVG chart ONLY from measured benchmark JSON; no sample metrics."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import sys


def create_svg(data: dict) -> str:
    cases = data.get('cases', {})
    if not cases or any(not value['validation']['equivalent'] for value in cases.values()):
        raise ValueError('Missing measured cases or failed semantic validation.')
    width, height = 1200, 165 + 175 * len(cases)
    bars = []
    for index, (name, case) in enumerate(cases.items()):
        baseline = float(case['baseline']['median_ms'])
        optimized = float(case['optimized']['median_ms'])
        if baseline < 0 or optimized < 0:
            raise ValueError('Negative timing supplied.')
        mx = max(baseline, optimized, .001)
        y = 122 + index * 175
        label = escape(name.replace('_', ' ').title())
        bars.extend([
            f'<text x="76" y="{y}" fill="#E8F2FF" font-size="27" font-weight="bold">{label}</text>',
            f'<rect x="80" y="{y+21}" width="{820*baseline/mx:.2f}" height="38" rx="9" fill="#735EC6"/>',
            f'<rect x="80" y="{y+69}" width="{820*optimized/mx:.2f}" height="38" rx="9" fill="#38CFE3"/>',
            f'<text x="935" y="{y+50}" fill="#E3DCFF" font-size="22">{baseline:.3f} ms</text>',
            f'<text x="935" y="{y+98}" fill="#B5F8FF" font-size="22">{optimized:.3f} ms</text>',
        ])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="18" fill="#0C142B"/>
<text x="75" y="56" fill="#EDF5FF" font-family="Arial" font-size="34" font-weight="bold">OBSERVED QUERY LATENCY</text>
<text x="77" y="83" fill="#92ACD3" font-family="Arial" font-size="18">Measured medians | Violet: baseline | Cyan: optimized | Lower is better</text>
<g font-family="Arial">{''.join(bars)}</g>
<text x="76" y="{height-24}" fill="#8295B9" font-family="Arial" font-size="16">Client wall-clock measurements · Includes fetch time · Environment dependent</text>
</svg>'''


def main():
    if len(sys.argv) != 3:
        raise SystemExit('Usage: python scripts/render_benchmark.py input.json output.svg')
    doc = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    svg = create_svg(doc)
    target = Path(sys.argv[2]); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(svg, encoding='utf-8')
    print('SVG written:', target)


if __name__ == '__main__':
    main()
