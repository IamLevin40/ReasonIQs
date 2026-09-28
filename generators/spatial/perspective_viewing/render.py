"""Draw real 3D faces and orthographic polygons as resolution-independent SVG."""

import math

from generators.spatial.misc.geometry import INK, STRUCTURE_PALETTES, svg_figure
from .projection import outward_face, hidden_cube_face


def source_figure(shapes, requested, palette="teal"):
    faces = []
    shades = STRUCTURE_PALETTES[palette]
    cube_origins = {tuple(shape["origin"]) for shape in shapes if shape["kind"] == "cube"}
    def project(p):
        x,y,z = p
        return ((y-x)*28,(x+y)*16-z*32)
    for shape in shapes:
        for face in shape["faces"]:
            vertices, normal = outward_face(shape, face)
            if sum(normal) <= 0 or hidden_cube_face(shape,normal,cube_origins):
                continue
            points = [project(p) for p in vertices]
            if len(set(points)) < 3:
                continue
            shade = shades["top"] if abs(normal[2]) else (shades["front"] if abs(normal[1]) else shades["side"])
            depth = sum(sum(p) for p in vertices)/len(vertices)
            faces.append((depth,points,shade,vertices))
    faces.sort(key=lambda face: face[0])
    minx=min(x for _,points,_,_ in faces for x,_ in points)
    miny=min(y for _,points,_,_ in faces for _,y in points)
    maxx=max(x for _,points,_,_ in faces for x,_ in points)
    maxy=max(y for _,points,_,_ in faces for _,y in points)
    object_left=72
    object_top=72
    object_right=object_left+maxx-minx
    object_bottom=object_top+maxy-miny
    width=object_right+75
    height=object_bottom+88
    body=[]
    for _,points,shade,_ in faces:
        path=" ".join(f"{x-minx+object_left:.1f},{y-miny+object_top:.1f}" for x,y in points)
        body.append(f'<polygon points="{path}" fill="{shade}" stroke="{INK}" stroke-width="1.7" stroke-linejoin="round"/>')
    arrows=[]
    directions={"Top":(0,0,-1),"Front":(0,-1,0),"Left":(-1,0,0)}
    placements={
        "Top":(((object_left+object_right)/2,14),((object_left+object_right)/2,53)),
        "Left":((14,object_bottom+47),(56,object_bottom+23)),
        "Front":((object_right+58,object_bottom+47),(object_right+16,object_bottom+23)),
    }
    labels={
        "Top":((object_left+object_right)/2+15,34),
        "Left":(14,object_bottom+75),
        "Front":(object_right+13,object_bottom+75),
    }
    for label in ("Top","Left","Front"):
        # One filled 2D polygon per arrow. Its direction matches the world
        # line of sight, and its placement identifies the corresponding face.
        vx,vy,vz=directions[label]
        start,tip=placements[label]
        dx,dy=tip[0]-start[0],tip[1]-start[1]
        length=math.hypot(dx,dy)
        ux,uy=dx/length,dy/length
        px,py=-uy,ux
        base=(tip[0]-ux*12,tip[1]-uy*12)
        dark=label==requested
        vertices=[(start[0]+px*3.5,start[1]+py*3.5),
                  (base[0]+px*3.5,base[1]+py*3.5),
                  (base[0]+px*10,base[1]+py*10),tip,
                  (base[0]-px*10,base[1]-py*10),
                  (base[0]-px*3.5,base[1]-py*3.5),
                  (start[0]-px*3.5,start[1]-py*3.5)]
        coords=" ".join(f"{x:.1f},{y:.1f}" for x,y in vertices)
        body.append(f'<polygon points="{coords}" fill="{INK if dark else "#cbd7dd"}" '
                    f'stroke="{INK if dark else "#7c909b"}" stroke-width="1.1"/>')
        label_x,label_y=labels[label]
        body.append(f'<text x="{label_x:.1f}" y="{label_y:.1f}" '
                    f'fill="{INK if dark else "#667c89"}" font-family="Arial" font-size="16" '
                    f'font-weight="{700 if dark else 400}">{label}</text>')
        arrows.append({"view":label,"world_direction":[vx,vy,vz],
                       "screen_start":start,"screen_tip":tip,
                       "screen_vertices":vertices,"highlighted":dark})
    return svg_figure("".join(body),width,height,f"3D object; arrow indicates {requested} viewpoint",
                      {"type":"solid-isometric","solids":shapes,"viewpoint":requested,
                       "palette":palette,"face_shades":shades,
                       "world_axes":{"Front":"+y toward -y","Left":"+x toward -x","Top":"+z toward -z"},
                       "object_bounds":[object_left,object_top,object_right,object_bottom],
                       "view_arrows":arrows},f"View from {requested}")


def view_figure(polys):
    points=[p for polygon in polys for p in polygon["vertices"]]
    minx=min(x for x,_ in points)
    miny=min(y for _,y in points)
    maxx=max(x for x,_ in points)
    maxy=max(y for _,y in points)
    unit=28
    body=[]
    for poly in polys:
        vertices=" ".join(f"{(x-minx)*unit+12:.1f},{(y-miny)*unit+12:.1f}" for x,y in poly["vertices"])
        body.append(f'<polygon points="{vertices}" fill="#eef3f5" stroke="{INK}" stroke-width="1.6" stroke-linejoin="round"/>')
    return svg_figure("".join(body),(maxx-minx)*unit+24,(maxy-miny)*unit+24,
                      "Orthographic view option",{"type":"orthographic-polygons","polygons":polys})
