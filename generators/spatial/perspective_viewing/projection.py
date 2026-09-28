"""Orthographic polygon projections and translation-invariant exact-grid signatures."""

from __future__ import annotations


# Viewer positions are +z (Top), +y (Front), and +x (Left).
# In the front image +x must appear left. Top keeps that same horizontal
# direction and places the near/front (+y) edge at the bottom of the image.
VIEWS = {"Top": 2, "Front": 1, "Left": 0}


def outward_face(shape, face):
    vertices = [shape["vertices"][index] for index in face]
    a,b,c = vertices[:3]
    u = tuple(b[i]-a[i] for i in range(3))
    v = tuple(c[i]-a[i] for i in range(3))
    normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    center = [sum(vertex[i] for vertex in shape["vertices"])/len(shape["vertices"]) for i in range(3)]
    face_center = [sum(vertex[i] for vertex in vertices)/len(vertices) for i in range(3)]
    if sum(normal[i]*(face_center[i]-center[i]) for i in range(3)) < 0:
        normal = tuple(-value for value in normal)
    return vertices, normal


def hidden_cube_face(shape, normal, cube_origins):
    if shape["kind"] != "cube":
        return False
    x,y,z = shape["origin"]
    direction = tuple(1 if n > 0 else -1 if n < 0 else 0 for n in normal)
    return (x+direction[0],y+direction[1],z+direction[2]) in cube_origins


def project(point, view):
    x, y, z = point
    if view == "Top":
        return (-x, y)
    if view == "Front":
        return (-x, -z)
    if view == "Left":
        return (y, -z)
    raise ValueError(f"Unknown view: {view}")


def polygons(shapes, view):
    """Project all real faces; nearer opaque faces paint over distant ones."""
    result = []
    depth_axis = VIEWS[view]
    cube_origins = {tuple(shape["origin"]) for shape in shapes if shape["kind"] == "cube"}
    for shape in shapes:
        for face in shape["faces"]:
            vertices, normal = outward_face(shape, face)
            if normal[depth_axis] <= 0 or hidden_cube_face(shape, normal, cube_origins):
                continue
            points = tuple(project(vertex, view) for vertex in vertices)
            if len(set(points)) < 3:
                continue
            depth = sum(vertex[depth_axis] for vertex in vertices) / len(vertices)
            result.append({"vertices": points, "world_vertices": vertices,
                           "depth": depth, "solid_kind": shape["kind"]})
    result.sort(key=lambda item: item["depth"])
    return result


def inside(point, polygon):
    x,y = point
    hit = False
    vertices = polygon
    for i,(ax,ay) in enumerate(vertices):
        bx,by = vertices[(i+1)%len(vertices)]
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            hit = not hit
    return hit


def _normalize_pixels(occupied):
    if not occupied:
        return frozenset()
    origin = (min(x for x,_ in occupied), min(y for _,y in occupied))
    return frozenset((x-origin[0],y-origin[1]) for x,y in occupied)


def signature(polys, scale=8):
    points = [vertex for polygon in polys for vertex in polygon["vertices"]]
    minx,maxx = min(p[0] for p in points), max(p[0] for p in points)
    miny,maxy = min(p[1] for p in points), max(p[1] for p in points)
    occupied = set()
    for ix in range(round(minx*scale), round(maxx*scale)):
        for iy in range(round(miny*scale), round(maxy*scale)):
            point = ((ix+.5)/scale,(iy+.5)/scale)
            if any(inside(point, polygon["vertices"]) for polygon in polys):
                occupied.add((ix,iy))
    return _normalize_pixels(occupied)


def raycast_signature(shapes, view, scale=8):
    """Independent solid-volume projection, with no face or SVG dependence."""
    projected = [project(vertex, view) for shape in shapes for vertex in shape["vertices"]]
    minx, maxx = min(x for x,_ in projected), max(x for x,_ in projected)
    miny, maxy = min(y for _,y in projected), max(y for _,y in projected)
    occupied = set()
    for ix in range(round(minx*scale), round(maxx*scale)):
        for iy in range(round(miny*scale), round(maxy*scale)):
            u,v = (ix+.5)/scale, (iy+.5)/scale
            for shape in shapes:
                x,y,z = shape["origin"]
                if view == "Top":
                    a,b = -u-x, v-y
                    inside = 0 < a < 1 and 0 < b < 1
                elif view == "Front":
                    a,b = -u-x, -v-z
                    inside = 0 < a < 1 and 0 < b < 1
                    if inside and shape["kind"] == "triangular-prism" and shape["slope_axis"] == "x":
                        inside = (b < a) if shape["high_at_positive_x"] else (b <= 1-a)
                else:
                    a,b = u-y, -v-z
                    inside = 0 < a < 1 and 0 < b < 1
                    if inside and shape["kind"] == "triangular-prism" and shape["slope_axis"] == "y":
                        inside = (b <= a) if shape["high_at_positive_x"] else (b < 1-a)
                if inside:
                    occupied.add((ix,iy))
                    break
    return _normalize_pixels(occupied)


def transform(polys, operation):
    def point(x,y):
        if operation == "mirror": return (-x,y)
        if operation == "rotate": return (-y,x)
        if operation == "flip": return (x,-y)
        return (x,y)
    return [{**polygon, "vertices": tuple(point(*p) for p in polygon["vertices"])}
            for polygon in polys]
