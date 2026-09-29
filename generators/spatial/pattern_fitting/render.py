"""SVG projection of structured vector art; no puzzle logic lives here."""

from __future__ import annotations

from generators.spatial.misc.geometry import svg_figure


def _path(item):
    points=item["points"]
    d="M"+" L".join(f"{x:.3f},{y:.3f}" for x,y in points)
    if item["kind"] == "fill":
        return f'<path d="{d} Z" fill="{item["fill"]}" stroke="none"/>'
    return (f'<path d="{d}" fill="none" stroke="{item.get("stroke", "#253746")}" '
            f'stroke-width="{item["stroke_width"]:.2f}" '
            'stroke-linecap="butt" stroke-linejoin="round"/>')


def puzzle_figure(master, box, mode):
    x0,y0,x1,y1=box
    outside=(f'<clipPath id="outside-hole">'
             f'<rect x="0" y="0" width="300" height="{y0}"/>'
             f'<rect x="0" y="{y1}" width="300" height="{300-y1}"/>'
             f'<rect x="0" y="{y0}" width="{x0}" height="{y1-y0}"/>'
             f'<rect x="{x1}" y="{y0}" width="{300-x1}" height="{y1-y0}"/>'
             '</clipPath>')
    art="".join(_path(item) for item in master)
    grid=''.join(f'<path d="M{n} 0 V300 M0 {n} H300" fill="none" stroke="#bbc9d1" stroke-width=".8"/>'
                 for n in (100,200))
    body=(f'<defs>{outside}</defs><g transform="translate(15 15)">'
          f'<rect width="300" height="300" fill="#ffffff" stroke="#253746" stroke-width="2"/>'
          f'<g clip-path="url(#outside-hole)">{grid}{art}</g>'
          f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" '
          'fill="#ffffff" stroke="#253746" stroke-width="2.4" stroke-dasharray="5 4"/>'
          f'<text x="{(x0+x1)/2}" y="{(y0+y1)/2+13}" text-anchor="middle" '
          'font-family="Arial,sans-serif" font-size="40" fill="#657b8a">?</text></g>')
    return svg_figure(body,330,330,f"Complete the {mode.lower()} in the continuous 3 by 3 pattern",
                      {"type":"pattern-fitting-puzzle","grid":[3,3],"missing_bounds":box,
                       "missing_mode":mode})


def choice_figure(piece, box, label):
    x0,y0,x1,y1=box
    # Identical viewport and scale for every option. The art itself is the
    # clipped vector geometry; no screenshot or regenerated approximation.
    art="".join(_path(item) for item in piece)
    body=(f'<defs><clipPath id="piece"><rect x="0" y="0" width="100" height="100"/></clipPath></defs>'
          '<g transform="translate(12 12) scale(1.7)">'
          '<rect width="100" height="100" fill="#ffffff"/>'
          f'<g clip-path="url(#piece)"><g transform="translate({-x0} {-y0})">{art}</g></g>'
          '<rect width="100" height="100" fill="none" stroke="#253746" stroke-width="1.4"/>'
          '</g>')
    return svg_figure(body,194,194,label,
                      {"type":"pattern-fitting-piece","bounds":box,"primitives":piece})
