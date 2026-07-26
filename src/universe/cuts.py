"""The contract a model's cut list must obey, and the ranges it implies.

Pure functions, no database. Reading a cuts run and materializing it are two
different jobs that must never disagree about what the run said, so the parse,
the check, the repair and the ranges live in one place both of them import.

A cut at N means block N opens a new passage; the first block is always a
start and is therefore never a cut.
"""

import json


def parse_cuts(response: str) -> list[int]:
    """The raw tool arguments as a list of ints, or a plain error."""
    data = json.loads(response)
    cuts = data.get("cuts")
    if not isinstance(cuts, list) or not all(isinstance(cut, int) for cut in cuts):
        raise ValueError(f"cuts is not a list of integers: {cuts!r}")
    return cuts


def check_cuts(cuts: list[int], seqs: list[int]) -> list[str]:
    """Every way the cuts deviate from the deterministic contract."""
    problems = []
    if cuts != sorted(cuts):
        problems.append("not ascending")
    if len(cuts) != len(set(cuts)):
        problems.append("duplicates")
    if seqs and seqs[0] in cuts:
        problems.append(f"includes the first block ({seqs[0]})")
    outside = [cut for cut in cuts if cut not in seqs]
    if outside:
        problems.append(f"outside the block range: {outside}")
    return problems


def repair_cuts(cuts: list[int], seqs: list[int]) -> list[int]:
    """The nearest valid reading of the cuts, for rendering after checking."""
    if not seqs:
        return []
    return sorted({cut for cut in cuts if cut in seqs} - {seqs[0]})


def passage_ranges(cuts: list[int], seqs: list[int]) -> list[tuple[int, int]]:
    """Consecutive (first_seq, last_seq) ranges the cuts imply."""
    if not seqs:
        return []
    starts = [seqs[0]] + cuts
    return [(start, stop - 1) for start, stop in zip(starts, starts[1:] + [seqs[-1] + 1])]
