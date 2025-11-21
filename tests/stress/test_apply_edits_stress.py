# tests/stress/test_apply_edits_stress.py
# Slow stress tests for large line sets & many edit ops

from __future__ import annotations

import random
import string
from typing import List, Dict

import pytest

from src.core.pipeline import apply_edits
from src.loom_io.types import Lines


# * Random text generator for stress input
def _random_text(length: int = 20) -> str:
    # generate random ascii text for stress inserts & replacements
    letters = string.ascii_letters + string.digits + " -_.,;:/()"
    return "".join(random.choice(letters) for _ in range(length))


@pytest.mark.slow
# * Stress test for apply_edits scalability & correctness
def test_apply_edits_large_input_many_ops() -> None:
    # create a large resume with 2000+ lines
    total_lines = 2000
    resume_lines: Lines = {
        i: f"Line {i} - {_random_text(10)}" for i in range(1, total_lines + 1)
    }

    # build 150+ mixed operations
    ops: List[Dict] = []

    # 60 single line replacements spread across file
    for i in range(1, 61):
        # spread across file: 5, 10, ..., 300
        line_num = 5 * i
        ops.append(
            {
                "op": "replace_line",
                "line": line_num,
                "text": f"Replaced {line_num} - {_random_text(25)}",
            }
        )

    # 50 insert_after ops, each inserting 2-3 lines, spaced out
    for i in range(1, 51):
        # spaced across file: 7, 14, ..., 350
        line_num = 7 * i
        insert_lines = "\n".join(_random_text(30) for _ in range(2 + (i % 2)))
        ops.append(
            {
                "op": "insert_after",
                "line": line_num,
                "text": insert_lines,
            }
        )

    # 40 replace_range ops; various sizes (1-4 lines) with 1-3 replacement lines
    # keep ranges in-bounds & non-overlapping by spacing
    start = 20
    for i in range(40):
        span = 1 + (i % 4)
        end = start + span - 1
        repl_count = 1 + (i % 3)
        repl_text = "\n".join(
            f"RX{i}-{j} {_random_text(15)}" for j in range(repl_count)
        )
        ops.append(
            {
                "op": "replace_range",
                "start": start,
                "end": end,
                "text": repl_text,
            }
        )
        # space ranges to reduce overlap effects
        start += 5

    # 10 delete ranges, modest size
    for i in range(10):
        start_del = 1500 + i * 3
        # delete 2 lines
        end_del = start_del + 1
        ops.append(
            {
                "op": "delete_range",
                "start": start_del,
                "end": end_del,
            }
        )

    edits = {"version": 1, "ops": ops}

    # apply edits; ensure no exceptions & structure is sane
    result = apply_edits(resume_lines, edits)

    # verify keys are contiguous starting at 1
    keys = sorted(result.keys())
    assert keys[0] == 1
    assert keys == list(range(1, keys[-1] + 1))

    # spot-check that a good number of replacements & inserts took effect
    assert sum("Replaced " in v for v in result.values()) >= 20
    assert any("RX0-0" in v for v in result.values())

    # ensure overall size stayed within a plausible bound (not exploding)
    # baseline +/- inserts/deletes/replacements — just guardrail against runaway growth
    assert 1500 <= len(result) <= 2600
