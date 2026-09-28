"""Resolution-independent jigsaw outlines and interior artwork."""

from __future__ import annotations

from generators.spatial.misc.geometry import INK, svg_figure
from .model import outline


def _points(vertices, shift=(0,0)):
    return " ".join(f"{x+shift[0]:.1f},{y+shift[1]:.1f}" for x,y in vertices)


def _art(piece, shift):
    body=[]
    for a,b in piece["lines"]:
        body.append(f'<line x1="{a[0]+shift[0]:.1f}" y1="{a[1]+shift[1]:.1f}" '
                    f'x2="{b[0]+shift[0]:.1f}" y2="{b[1]+shift[1]:.1f}" '
                    f'stroke="{INK}" stroke-width="2.3" stroke-linecap="round"/>')
    body.append(f'<polygon points="{_points(piece["icon"],shift)}" fill="#ffffff" '
                f'stroke="{INK}" stroke-width="2.3" stroke-linejoin="round"/>')
    return "".join(body)


def piece_figure(piece):
    vertices=outline(piece)
    minx,miny=min(x for x,_ in vertices),min(y for _,y in vertices)
    maxx,maxy=max(x for x,_ in vertices),max(y for _,y in vertices)
    shift=(12-minx,12-miny)
    body=(f'<polygon points="{_points(vertices,shift)}" fill="#f4f7f8" '
          f'stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
          +_art(piece,shift))
    return svg_figure(body,maxx-minx+24,maxy-miny+24,
                      "Loose jigsaw piece with line and polygon artwork",
                      {"type":"jigsaw-piece","outline_vertices":vertices,
                       "icon_polygon":piece["icon"],"lines":piece["lines"],
                       "edges":piece["edges"],"piece_id":piece["id"]})


def detached_figures(pieces):
    return [piece_figure(piece) for piece in pieces]


def choice_figure(board):
    size=board["size"]
    body=[]
    geometry=[]
    for index,piece in enumerate(board["tiles"]):
        row,col=divmod(index,size)
        shift=(12+col*100,12+row*100)
        vertices=outline(piece)
        body.append(f'<polygon points="{_points(vertices,shift)}" fill="#f4f7f8" '
                    f'stroke="{INK}" stroke-width="1.7" stroke-linejoin="round"/>')
        geometry.append({"slot":[col,row],"outline_vertices":vertices,
                         "icon_polygon":piece["icon"],"lines":piece["lines"],
                         "edges":piece["edges"]})
    for index,piece in enumerate(board["tiles"]):
        row,col=divmod(index,size)
        body.append(_art(piece,(12+col*100,12+row*100)))
    body.append(f'<rect x="12" y="12" width="{size*100}" height="{size*100}" '
                f'fill="none" stroke="{INK}" stroke-width="2.7"/>')
    side=size*100+24
    return svg_figure("".join(body),side,side,"Completed square jigsaw option",
                      {"type":"square-jigsaw-board","grid_size":size,
                       "aspect_ratio":[1,1],"tiles":geometry,
                       "allow_reflection":False})
