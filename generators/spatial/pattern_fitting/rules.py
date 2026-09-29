"""Build complete, layered compositions before a hole is selected."""

from __future__ import annotations

import math

from .geometry import circle, clip_primitive, polygon, primitive, regular

LIGHT = "#ffffff"
DARK = "#627689"
BACKGROUND_STROKE = "#66879b"
TEXTURE_STROKE = "#50758a"
MOTIF_STROKE = "#193b55"


def _rotate(points, cx, cy, angle):
    c, s = math.cos(angle), math.sin(angle)
    return [(cx+x*c-y*s, cy+x*s+y*c) for x, y in points]


def _lines(rng, layer, family):
    result = []
    rules = {"layer_id": layer, "family": family}
    if family in ("parallel", "crossed", "grid", "progressive_stripes"):
        angle = rng.choice((0, math.pi/2, math.pi/4, -math.pi/4))
        if family == "grid": angle = 0
        spacing = rng.choice((30, 40, 50))
        phase = rng.choice((0, spacing//2))
        angles = [angle]
        if family == "crossed": angles.append(angle+math.pi/2)
        if family == "grid": angles = [0, math.pi/2]
        if family == "progressive_stripes": angles = [0, math.pi/4, math.pi/2]
        for direction, theta in enumerate(angles):
            nx, ny = -math.sin(theta), math.cos(theta)
            tx, ty = math.cos(theta), math.sin(theta)
            for k in range(-18, 19):
                d = k*spacing+phase
                cx, cy = 150+nx*d, 150+ny*d
                item = primitive(layer, [(cx-500*tx, cy-500*ty), (cx+500*tx, cy+500*ty)],
                                 width=1.5 if family == "crossed" else 1.8,
                                 stroke=BACKGROUND_STROKE,
                                 role="stripe", phase=phase)
                if family == "progressive_stripes":
                    result.extend(clip_primitive(item,(0,direction*100,300,(direction+1)*100)))
                else:
                    result.append(item)
        rules.update(spacing=spacing, phase=phase, orientations=[round(math.degrees(a)) for a in angles])
    elif family in ("wave", "zigzag"):
        spacing = rng.choice((36, 42, 48))
        amplitude = rng.choice((7, 10))
        phase = rng.choice((0, 18))
        for baseline in range(-50, 370, spacing):
            points = []
            for x in range(-20, 322, 4):
                if family == "wave":
                    y = baseline+amplitude*math.sin((x+phase)*2*math.pi/72)
                else:
                    t = ((x+phase) % 64)/64
                    y = baseline+amplitude*(4*abs(t-.5)-1)
                points.append((x, y))
            result.append(primitive(layer, points, width=1.8, stroke=BACKGROUND_STROKE,
                                    role="curve", phase=phase))
        rules.update(spacing=spacing, amplitude=amplitude, phase=phase, orientation="horizontal")
    elif family == "radial":
        count = rng.choice((8, 10, 12))
        phase = rng.choice((0, math.pi/12, math.pi/8))
        for i in range(count):
            a = phase+2*math.pi*i/count
            result.append(primitive(layer, [(150, 150), (150+225*math.cos(a), 150+225*math.sin(a))],
                                    width=1.8, stroke=BACKGROUND_STROKE,
                                    role="radial", phase=round(phase, 4)))
        rules.update(count=count, center=[150, 150], rotational_symmetry=count)
    else:  # concentric
        spacing = rng.choice((34, 42, 50))
        for radius in range(spacing, 215, spacing):
            result.append(primitive(layer, circle(150, 150, radius), width=1.8,
                                    stroke=BACKGROUND_STROKE, role="ring", phase=spacing))
        rules.update(spacing=spacing, center=[150, 150], closure="concentric circles")
    return result, rules


def _motif(layer, shape, cx, cy, radius, angle, shaded):
    """Return one opaque foreground motif in a light or dark shade."""
    def world(local): return _rotate(local, cx, cy, angle)
    fill = DARK if shaded else LIGHT
    if shape in ("circle", "ellipse", "ring", "concentric", "semicircle", "quarter_circle", "arc"):
        if shape in ("semicircle", "quarter_circle", "arc"):
            sweep = {"semicircle": math.pi, "quarter_circle": math.pi/2, "arc": 1.45*math.pi}[shape]
            points = world(circle(0, 0, radius, start=-math.pi/2, sweep=sweep, steps=40))
            if shape == "arc":
                inside = world(circle(0, 0, radius-12, start=-math.pi/2,
                                      sweep=sweep, steps=40))
                return polygon(layer, points+inside[::-1], fill=fill, width=2.7,
                               stroke=MOTIF_STROKE, role="closure")
            return polygon(layer, [(cx, cy)]+points, fill=fill, width=2.7,
                           stroke=MOTIF_STROKE, role="closure")
        ry = radius*.68 if shape == "ellipse" else radius
        outer = world(circle(0, 0, radius, ry))
        result = [primitive(layer, outer[:-1], kind="fill", fill=fill, width=0, role="closure")]
        if shape in ("ring", "concentric"):
            middle=world(circle(0, 0, radius*.64, ry*.64))
            result.append(primitive(layer, middle[:-1], kind="fill", fill=LIGHT,
                                    width=0, role="closure"))
        if shape == "concentric":
            inner=world(circle(0, 0, radius*.32, ry*.32))
            result.append(primitive(layer, inner[:-1], kind="fill", fill=fill,
                                    width=0, role="closure"))
        result.append(primitive(layer, outer, width=2.7, stroke=MOTIF_STROKE, role="closure"))
        if shape in ("ring", "concentric"):
            result.append(primitive(layer, middle, width=2.3, stroke=MOTIF_STROKE,
                                    role="closure"))
        if shape == "concentric":
            result.append(primitive(layer, inner, width=2, stroke=MOTIF_STROKE,
                                    role="closure"))
        return result
    if shape == "star":
        local = [(radius*(1 if i % 2 == 0 else .47)*math.cos(-math.pi/2+i*math.pi/5),
                  radius*(1 if i % 2 == 0 else .47)*math.sin(-math.pi/2+i*math.pi/5)) for i in range(10)]
    elif shape == "cross":
        r, a = radius, radius*.37
        local = [(-a,-r),(a,-r),(a,-a),(r,-a),(r,a),(a,a),(a,r),(-a,r),(-a,a),(-r,a),(-r,-a),(-a,-a)]
    elif shape == "chevron":
        r = radius
        local = [(-r,-r*.55),(0,r*.1),(r,-r*.55),(r,r*.05),(0,r*.7),(-r,r*.05)]
    elif shape == "irregular_polygon":
        local = [(-radius*.9,-radius*.4),(-radius*.1,-radius),(radius*.85,-radius*.55),
                 (radius*.72,radius*.65),(-radius*.35,radius),(-radius,radius*.2)]
    elif shape == "diamond":
        local = [(0,-radius),(radius,0),(0,radius),(-radius,0)]
    else:
        sides = {"triangle":3,"square":4,"pentagon":5,"hexagon":6,"octagon":8}[shape]
        local = regular(0, 0, radius, radius, sides, -math.pi/2)
    return polygon(layer, world(local), fill=fill, width=2.7,
                   stroke=MOTIF_STROKE, role="motif")


SHAPES = ("circle", "ellipse", "ring", "concentric", "semicircle", "quarter_circle",
          "arc", "star", "cross", "chevron", "irregular_polygon", "diamond",
          "triangle", "square", "pentagon", "hexagon", "octagon")


def _motifs(rng, layer):
    family = rng.choice(("rotating_junctions", "repeating_cells", "central_closure",
                         "mirrored_neighbors", "perimeter_repeat"))
    shape = rng.choice(SHAPES)
    shaded = rng.random() < .45
    alternating = family in ("rotating_junctions", "repeating_cells", "perimeter_repeat") and rng.random() < .55
    result = []
    placements = []
    if family == "rotating_junctions":
        placements = [(80,80,0), (220,80,math.pi/2), (220,220,math.pi), (80,220,3*math.pi/2)]
        radius = rng.choice((54,58,62))
    elif family == "repeating_cells":
        placements = [(x,y,(r+c)%4*math.pi/2) for r,y in enumerate((50,150,250))
                      for c,x in enumerate((50,150,250))]
        radius = rng.choice((34,38,42))
    elif family == "central_closure":
        placements = [(150,150,0)]
        radius = rng.choice((86,92,96))
    elif family == "mirrored_neighbors":
        placements = [(80,150,0),(220,150,math.pi)]
        radius = rng.choice((54,58,62))
    else:
        placements = [(50,50,0),(150,50,math.pi/2),(250,50,math.pi),
                      (250,150,3*math.pi/2),(250,250,0),(150,250,math.pi/2),
                      (50,250,math.pi),(50,150,3*math.pi/2)]
        radius = rng.choice((34,38,42))
    if family == "mirrored_neighbors":
        first=_motif(layer,shape,80,150,radius,0,shaded)
        result.extend(first)
        result.extend({**item,"points":[[300-x,y] for x,y in item["points"]]} for item in first)
    else:
        for i, (x,y,a) in enumerate(placements):
            result.extend(_motif(layer, shape, x,y,radius,a,
                                 (i%2 == 0) if alternating else shaded))
    return result, {"layer_id":layer,"family":family,"shape":shape,"radius":radius,
                    "transforms":"quarter-turn cycle" if family in ("rotating_junctions", "repeating_cells", "perimeter_repeat") else
                                 "vertical reflection" if family == "mirrored_neighbors" else "closure",
                    "placements":[[x,y,round(math.degrees(a))] for x,y,a in placements],
                    "alternating_fill":alternating,"shade_values":{"shaded":DARK,"unshaded":LIGHT}}


def _texture(rng, layer, quiet=False):
    choices=("dots", "square_dots", "short_marks", "checker", "alternating_quadrants") if quiet else \
            ("dots", "square_dots", "short_marks", "cross_hatch", "checker",
             "diagonal_stripes", "alternating_quadrants")
    family = rng.choice(choices)
    result = []
    spacing = rng.choice((36, 40, 50))
    phase = spacing//2
    if family in ("dots", "square_dots", "short_marks"):
        for y in range(phase, 301, spacing):
            for x in range(phase, 301, spacing):
                if family == "dots":
                    points = circle(x,y,2.1,steps=12)[:-1]
                    result.append(primitive(layer, points, kind="fill", fill=DARK, width=0,
                                            role="dot", phase=phase))
                elif family == "square_dots":
                    result.append(primitive(layer, [(x-2,y-2),(x+2,y-2),(x+2,y+2),(x-2,y+2)],
                                            kind="fill", fill=DARK, width=0, role="dot", phase=phase))
                else:
                    result.append(primitive(layer, [(x-3,y-2),(x+3,y+2)], width=1.5,
                                            stroke=TEXTURE_STROKE,
                                            role="mark", phase=phase))
    elif family in ("cross_hatch", "diagonal_stripes"):
        angles = (math.pi/4,-math.pi/4) if family == "cross_hatch" else (rng.choice((math.pi/4,-math.pi/4)),)
        for angle in angles:
            nx,ny = -math.sin(angle),math.cos(angle)
            tx,ty = math.cos(angle),math.sin(angle)
            for k in range(-18,19):
                d=k*spacing+phase
                cx,cy=150+nx*d,150+ny*d
                result.append(primitive(layer, [(cx-450*tx,cy-450*ty),(cx+450*tx,cy+450*ty)],
                                        width=1.1,stroke=TEXTURE_STROKE,
                                        role="texture",phase=phase))
    elif family == "checker":
        for row,y in enumerate(range(20,300,40)):
            for col,x in enumerate(range(20,300,40)):
                if (row+col)%2 == 0:
                    result.append(primitive(layer, [(x-5,y-5),(x+5,y-5),
                                                    (x+5,y+5),(x-5,y+5)],
                                            kind="fill",fill=DARK,width=0,role="shade"))
    else:
        for row in range(3):
            for col in range(3):
                if (row+col)%2 == 0:
                    x,y=col*100+50,row*100+50
                    result.append(primitive(layer, [(x-12,y-12),(x+12,y-12),(x-12,y+12)],
                                            kind="fill",fill=DARK,width=0,role="shade"))
    return result, {"layer_id":layer,"family":family,"spacing":spacing,"phase":phase}


def build_master(rng, difficulty):
    """Return complete art and declarative rule layers, independent of a hole."""
    master, rules = [], []
    if difficulty == "Easy" and rng.random() < .42:
        art, rule = _motifs(rng, "motif")
        master.extend(art); rules.append(rule)
    else:
        family = rng.choice(("parallel","crossed","grid","wave","zigzag","radial","concentric",
                             "progressive_stripes"))
        art, rule = _lines(rng, "lines", family)
        master.extend(art); rules.append(rule)
    if difficulty != "Easy":
        art, rule = _motifs(rng, "motif")
        master.extend(art); rules.append(rule)
        if difficulty == "Challenge" or rng.random() < .4:
            art, rule = _texture(rng, "texture", quiet=difficulty == "Challenge")
            # Texture goes below contour layers in painting order.
            master = art+master; rules.insert(0,rule)
    return master, rules
