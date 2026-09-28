"""Exact square-jigsaw fitting under translations and quarter turns only."""

from __future__ import annotations

from .model import SIDES, outline, rotate_piece


def area2(vertices):
    return abs(sum(x1*y2-x2*y1 for (x1,y1),(x2,y2)
                   in zip(vertices,vertices[1:]+vertices[:1])))


def valid_square(board):
    size=board.get("size")
    tiles=board.get("tiles")
    if not isinstance(size,int) or size<2 or not isinstance(tiles,list) or len(tiles)!=size*size:
        return False
    total_area2=0
    for row in range(size):
        for col in range(size):
            tile=tiles[row*size+col]
            if set(tile.get("edges",{}))!=set(SIDES) or not tile.get("icon") or not tile.get("lines"):
                return False
            edges=tile["edges"]
            if row==0 and edges["N"]["sign"]!=0:return False
            if col==0 and edges["W"]["sign"]!=0:return False
            if row==size-1 and edges["S"]["sign"]!=0:return False
            if col==size-1 and edges["E"]["sign"]!=0:return False
            if col+1<size:
                neighbor=tiles[row*size+col+1]["edges"]["W"]
                if edges["E"]["sign"]==0 or edges["E"]["sign"]!=-neighbor["sign"] or edges["E"]["profile"]!=neighbor["profile"]:
                    return False
            if row+1<size:
                neighbor=tiles[(row+1)*size+col]["edges"]["N"]
                if edges["S"]["sign"]==0 or edges["S"]["sign"]!=-neighbor["sign"] or edges["S"]["profile"]!=neighbor["profile"]:
                    return False
            total_area2+=area2(outline(tile))
    return total_area2==2*(size*100)**2


def _cyclic(vertices):
    vertices=tuple(tuple(p) for p in vertices)
    return min(vertices[i:]+vertices[:i] for i in range(len(vertices)))


def tile_signature(tile):
    edges=tuple((tile["edges"][side]["sign"],
                 tuple(tile["edges"][side]["profile"] or ())) for side in SIDES)
    lines=tuple(sorted(tuple(sorted((tuple(a),tuple(b)))) for a,b in tile["lines"]))
    return edges,_cyclic(tile["icon"]),lines


def board_signature(board):
    return tuple(tile_signature(tile) for tile in board["tiles"])


def fit(board, pieces):
    """Assign each supplied detached piece once to a precise square slot."""
    if not valid_square(board) or len(pieces)!=board["size"]**2:
        return None
    available={}
    for index,piece in enumerate(pieces):
        for turns in range(4):
            available.setdefault(tile_signature(rotate_piece(piece,turns)),[]).append((index,turns))
    choices=[]
    for tile in board["tiles"]:
        matches=available.get(tile_signature(tile),[])
        if not matches:
            return None
        choices.append(matches)
    order=sorted(range(len(choices)),key=lambda slot:len(choices[slot]))

    def search(position,used,solution):
        if position==len(order):
            return solution
        slot=order[position]
        for piece_index,turns in choices[slot]:
            if piece_index in used:
                continue
            result=search(position+1,used|{piece_index},
                          {**solution,slot:{"piece_index":piece_index,"turns":turns}})
            if result is not None:
                return result
        return None

    return search(0,set(),{})
