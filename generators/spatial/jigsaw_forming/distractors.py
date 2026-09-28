"""Plausible complete square pictures that the supplied pieces cannot make."""

from __future__ import annotations

from copy import deepcopy

from .model import PROFILES, rotate_board, rotate_point
from .solver import board_signature, fit, valid_square


def mutate(rng, board):
    candidate=deepcopy(board)
    tiles=candidate["tiles"]
    action=rng.choice(("swap-art", "turn-art", "connector"))
    if action=="swap-art":
        a,b=rng.sample(range(len(tiles)),2)
        tiles[a]["icon"],tiles[b]["icon"]=tiles[b]["icon"],tiles[a]["icon"]
    elif action=="turn-art":
        index=rng.randrange(len(tiles))
        turns=rng.randrange(1,4)
        tiles[index]["icon"]=[rotate_point(point,turns) for point in tiles[index]["icon"]]
    else:
        size=board["size"]
        seams=[]
        for row in range(size):
            for col in range(size):
                index=row*size+col
                if col+1<size:seams.append((index,"E",index+1,"W"))
                if row+1<size:seams.append((index,"S",index+size,"N"))
        a,side_a,b,side_b=rng.choice(seams)
        old=tiles[a]["edges"][side_a]["profile"]
        # Keep seam depth so line artwork still meets at the connector tip.
        options=[profile for profile in PROFILES if profile[1]==old[1] and list(profile)!=old]
        profile=list(rng.choice(options))
        tiles[a]["edges"][side_a]["profile"]=profile
        tiles[b]["edges"][side_b]["profile"]=profile.copy()
    return candidate,action


def candidates(rng, board, detached, choice_count):
    correct=rotate_board(board,rng.randrange(4))
    options=[correct]
    reasons=["exact assembly"]
    seen={board_signature(correct)}
    attempts=0
    while len(options)<choice_count and attempts<900:
        attempts+=1
        changed,reason=mutate(rng,board)
        candidate=rotate_board(changed,rng.randrange(4))
        key=board_signature(candidate)
        if key in seen or not valid_square(candidate) or fit(candidate,detached) is not None:
            continue
        seen.add(key)
        options.append(candidate)
        reasons.append(reason)
    if len(options)!=choice_count:
        raise RuntimeError("Could not create enough impossible square jigsaws")
    paired=list(zip(options,reasons))
    rng.shuffle(paired)
    return [item[0] for item in paired],[item[1] for item in paired]
