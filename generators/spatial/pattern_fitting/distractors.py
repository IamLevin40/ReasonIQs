"""Plausible geometric mutations of an authoritative clipped piece."""

from __future__ import annotations

import math

from .geometry import clip_pattern, signature, visible_signature
from .rules import DARK, LIGHT


def _transform(piece, box, name):
    cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
    def point(x, y):
        u,v=x-cx,y-cy
        if name == "rotate_90": return [cx-v,cy+u]
        if name == "rotate_180": return [cx-u,cy-v]
        if name == "rotate_270": return [cx+v,cy-u]
        if name == "reflect_horizontal": return [cx+u,cy-v]
        if name == "reflect_vertical": return [cx-u,cy+v]
        if name == "reflect_diagonal": return [cx+v,cy+u]
        if name == "reflect_anti_diagonal": return [cx-v,cy-u]
        raise ValueError(name)
    return [{**item,"points":[point(x,y) for x,y in item["points"]]} for item in piece]


def _shift_master(master, box, role, dx, dy):
    changed=[]
    for item in master:
        if item["role"] in role:
            changed.append({**item,"points":[[x+dx,y+dy] for x,y in item["points"]],
                            "phase":item["phase"]+dx+dy})
        else:
            changed.append(item)
    return clip_pattern(changed,box)


def _scale_contour(master, box, factor):
    closure=[item for item in master if item["role"] == "closure"]
    if not closure:
        return None
    target=closure[0]
    xs=[p[0] for p in target["points"]]; ys=[p[1] for p in target["points"]]
    cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2
    changed=[]
    for item in master:
        if item["layer_id"] == target["layer_id"] and item["role"] == "closure":
            changed.append({**item,"points":[[cx+(x-cx)*factor,cy+(y-cy)*factor] for x,y in item["points"]]})
        else:
            changed.append(item)
    return clip_pattern(changed,box)


def _shade_swap(piece):
    result=[]
    for item in piece:
        if item["kind"] == "fill" and item["fill"] in (DARK,LIGHT):
            shade=LIGHT if item["fill"] == DARK else DARK
            result.append({**item,"fill":shade})
        else:
            result.append(item)
    return result


def _partial_reflection(piece, box, roles):
    reflected=_transform(piece,box,"reflect_vertical")
    return [other if item["role"] in roles else item
            for item,other in zip(piece,reflected)]


def _endpoint_shift(piece, box):
    x0,y0,x1,y1=box
    for index,item in enumerate(piece):
        if item["kind"] != "stroke" or len(item["points"]) < 2:
            continue
        x,y=item["points"][0]
        moved=None
        if abs(x-x0)<1e-7 or abs(x-x1)<1e-7:
            moved=[x,min(y1,max(y0,y+7))]
        elif abs(y-y0)<1e-7 or abs(y-y1)<1e-7:
            moved=[min(x1,max(x0,x+7)),y]
        if moved and moved != [x,y]:
            result=list(piece)
            result[index]={**item,"points":[moved]+item["points"][1:]}
            return result
    return None


def _ink_score(piece):
    score=0.0
    for item in piece:
        points=item["points"]
        if item["kind"] == "stroke":
            score+=sum(math.dist(a,b) for a,b in zip(points,points[1:]))*item["stroke_width"]
        else:
            area=abs(sum(a[0]*b[1]-b[0]*a[1]
                         for a,b in zip(points,points[1:]+points[:1])))/2
            opacity={LIGHT:0,DARK:.6}.get(item["fill"],.3)
            score+=area*opacity
    return score


def generate(master, correct, box, count, rng):
    mutations=["rotate_90","rotate_180","rotate_270","reflect_horizontal",
               "reflect_vertical","reflect_diagonal","reflect_anti_diagonal",
               "shift_stripes_6","shift_stripes_10","shift_stripes_minus_7",
               "shift_motif_8","shift_motif_minus_8","change_arc_radius",
               "swap_shading","reflect_motif_only","reflect_texture_only",
               "shift_one_endpoint"]
    rng.shuffle(mutations)
    seen={signature(correct)}
    seen_visible={visible_signature(correct,grayscale=True)}
    reference_ink=_ink_score(correct)
    options=[(correct,"exact clipped piece")]
    for name in mutations:
        if name in ("rotate_90","rotate_180","rotate_270","reflect_horizontal",
                    "reflect_vertical","reflect_diagonal","reflect_anti_diagonal"):
            piece=_transform(correct,box,name)
        elif name.startswith("shift_stripes"):
            amount={"shift_stripes_6":6,"shift_stripes_10":10,"shift_stripes_minus_7":-7}[name]
            piece=_shift_master(master,box,{"stripe","texture","curve","mark","dot","radial","ring"},amount,0)
        elif name.startswith("shift_motif"):
            piece=_shift_master(master,box,{"motif","closure"},8 if name.endswith("_8") else -8,0)
        elif name == "change_arc_radius":
            piece=_scale_contour(master,box,1.09)
        elif name == "reflect_motif_only":
            piece=_partial_reflection(correct,box,{"motif","closure"})
        elif name == "reflect_texture_only":
            piece=_partial_reflection(correct,box,{"stripe","texture","dot","mark","shade"})
        elif name == "shift_one_endpoint":
            piece=_endpoint_shift(correct,box)
        else:
            piece=_shade_swap(correct)
        if not piece:
            continue
        sig=signature(piece)
        visible=visible_signature(piece,grayscale=True)
        if sig in seen or visible in seen_visible:
            continue
        # A missing stroke layer cannot count as a plausible subtle error.
        if abs(len(piece)-len(correct)) > max(3,len(correct)*.28):
            continue
        if reference_ink and not .78 <= _ink_score(piece)/reference_ink <= 1.22:
            continue
        seen.add(sig)
        seen_visible.add(visible)
        options.append((piece,name))
        if len(options) == count:
            rng.shuffle(options)
            return options
    raise ValueError("Not enough distinct geometric distractors")
