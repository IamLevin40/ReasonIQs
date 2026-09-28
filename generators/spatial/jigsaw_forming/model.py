"""Procedural square jigsaws with exact connector and artwork geometry."""

from __future__ import annotations

from copy import deepcopy

SIDES = ("N", "E", "S", "W")
SIDE_INDEX = {side: index for index, side in enumerate(SIDES)}
OPPOSITE = {"N":"S", "E":"W", "S":"N", "W":"E"}
SIZE = {"Easy":2, "Average":3, "Challenge":3}

# Integer local coordinates use a 100 by 100 nominal tile. Connectors occupy
# the interior seams only; the assembled outside stays exactly square.
PROFILES = [(span, depth) for span in (34,40,46,52) for depth in (12,16,20)]
ICONS = (
    ((50,34),(65,62),(35,62)),
    ((50,31),(69,50),(50,69),(31,50)),
    ((35,35),(65,35),(65,65),(35,65)),
    ((50,31),(68,44),(61,67),(39,67),(32,44)),
    ((50,31),(66,40),(66,60),(50,69),(34,60),(34,40)),
    ((35,38),(65,38),(57,62),(43,62)),
    ((37,33),(63,33),(63,44),(54,44),(54,67),(46,67),(46,44),(37,44)),
    ((50,32),(58,43),(70,43),(61,52),(65,66),(50,59),(35,66),(39,52),(30,43),(42,43)),
    ((36,36),(64,36),(64,45),(56,45),(56,64),(44,64),(44,45),(36,45)),
)


def edge(sign=0, profile=None):
    return {"sign":sign, "profile":list(profile) if profile else None}


def point(side, t, outward=0):
    """Clockwise side point with positive offset toward the piece exterior."""
    if side == "N": return (t, -outward)
    if side == "E": return (100+outward, t)
    if side == "S": return (100-t, 100+outward)
    if side == "W": return (-outward, 100-t)
    raise ValueError(side)


def outline(piece):
    vertices = []
    for side in SIDES:
        descriptor = piece["edges"][side]
        if descriptor["sign"]:
            span, depth = descriptor["profile"]
            start, end = (100-span)//2, (100+span)//2
            stations = ((0,0),(start,0),(start+6,descriptor["sign"]*depth),
                        (end-6,descriptor["sign"]*depth),(end,0),(100,0))
        else:
            stations = ((0,0),(100,0))
        vertices.extend(point(side,t,d) for t,d in stations[:-1])
    return vertices


def rotate_point(vertex, turns):
    x,y = vertex
    for _ in range(turns % 4):
        x,y = 100-y,x
    return (x,y)


def rotate_piece(piece, turns):
    turns %= 4
    result = deepcopy(piece)
    for _ in range(turns):
        result["edges"] = {side:deepcopy(result["edges"][SIDES[(SIDE_INDEX[side]-1)%4]])
                                   for side in SIDES}
        result["icon"] = [rotate_point(vertex,1) for vertex in result["icon"]]
        result["lines"] = [[rotate_point(a,1),rotate_point(b,1)] for a,b in result["lines"]]
    return result


def line_art(piece, active_sides):
    lines=[]
    for side in SIDES:
        if side not in active_sides:
            continue
        descriptor=piece["edges"][side]
        outward=descriptor["sign"]*descriptor["profile"][1] if descriptor["sign"] else 0
        lines.append([(50,50),point(side,50,outward)])
    return lines


def make_board(rng, difficulty):
    size=SIZE[difficulty]
    profiles=rng.sample(PROFILES,2*size*(size-1))
    pieces=[{"id":f"piece-{index+1}","edges":{side:edge() for side in SIDES},
             "icon":[],"lines":[]} for index in range(size*size)]
    seams=[]
    cursor=0
    for row in range(size):
        for col in range(size):
            here=row*size+col
            for side,other in (("E",here+1 if col+1<size else None),
                               ("S",here+size if row+1<size else None)):
                if other is None:
                    continue
                profile=profiles[cursor]; cursor+=1
                sign=rng.choice((-1,1))
                pieces[here]["edges"][side]=edge(sign,profile)
                pieces[other]["edges"][OPPOSITE[side]]=edge(-sign,profile)
                seams.append((here,side,other,OPPOSITE[side]))
    active=[set() for _ in pieces]
    probability={"Easy":1.0,"Average":.82,"Challenge":.7}[difficulty]
    for a,side_a,b,side_b in seams:
        if rng.random()<probability:
            active[a].add(side_a); active[b].add(side_b)
    artwork=rng.sample(ICONS,len(pieces)) if difficulty=="Average" else None
    for index,piece in enumerate(pieces):
        if not active[index]:
            available=[side for side in SIDES if piece["edges"][side]["sign"]]
            if available:
                chosen=rng.choice(available)
                active[index].add(chosen)
                neighbor=index+{"N":-size,"E":1,"S":size,"W":-1}[chosen]
                active[neighbor].add(OPPOSITE[chosen])
    for index,piece in enumerate(pieces):
        if difficulty=="Easy":
            shape=ICONS[index]
        elif difficulty=="Average":
            shape=artwork[index]
        else:
            shape=rng.choice(ICONS[:5])
        turns=rng.randrange(4)
        piece["icon"]=[rotate_point(vertex,turns) for vertex in shape]
        piece["lines"]=line_art(piece,active[index])
    return {"size":size,"tiles":pieces}


def rotate_board(board, turns):
    size=board["size"]
    result=[None]*(size*size)
    for row in range(size):
        for col in range(size):
            nr,nc=row,col
            for _ in range(turns%4):
                nr,nc=nc,size-1-nr
            result[nr*size+nc]=rotate_piece(board["tiles"][row*size+col],turns)
    return {"size":size,"tiles":result}
