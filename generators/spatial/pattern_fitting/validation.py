"""Exact reinsertion and boundary-connection checks."""

from __future__ import annotations

from .geometry import boundary_connections, clip_pattern, signature, visible_signature


def validate(master, box, options, correct_index):
    authoritative=clip_pattern(master,box)
    expected=signature(authoritative)
    signatures=[signature(piece) for piece,_ in options]
    if signatures[correct_index] != expected or signatures.count(expected) != 1:
        return False
    if len(set(signatures)) != len(signatures):
        return False
    visible=[visible_signature(piece, grayscale=True) for piece,_ in options]
    if len(set(visible)) != len(visible) or visible[correct_index] != visible_signature(authoritative, grayscale=True):
        return False
    boundary=boundary_connections(authoritative,box)
    if len(boundary) < 2:
        return False
    # Equality with the master is the global reconstruction test. A candidate
    # may agree at every edge yet still violate closure or an interior motif.
    return all(sig != expected for i,sig in enumerate(signatures) if i != correct_index)


def violation(master, box, piece):
    expected=boundary_connections(clip_pattern(master,box),box)
    found=boundary_connections(piece,box)
    if expected != found:
        return "boundary connection or pattern phase"
    return "interior closure, repetition, or symmetry"
