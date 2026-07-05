"""Recursive character splitting for instructional prose.

Splits on the most semantically meaningful separator available (paragraph →
line → sentence → word) and only degrades to harder cuts when a fragment is
still too large, so repair steps stream to the user without sentences cut off
mid-step. Adjacent chunks share a configurable overlap so no instruction loses
its lead-in context at a chunk boundary.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

DEFAULT_SEPARATORS: tuple[str, ...] = ("\n\n", "\n", ". ", " ", "")


def estimate_tokens(text: str, chars_per_token: int = 4) -> int:
    """Cheap token estimate; see ChunkingConfig.chars_per_token."""
    return math.ceil(len(text) / chars_per_token)


class RecursiveCharacterSplitter:
    """Character-budget splitter with separator-aware recursion and overlap.

    ``chunk_size_chars`` is a soft ceiling: a chunk may exceed it by at most
    one separator's length, never by a whole fragment.
    """

    def __init__(
        self,
        chunk_size_chars: int,
        overlap_chars: int,
        separators: Sequence[str] = DEFAULT_SEPARATORS,
    ) -> None:
        if not 0 <= overlap_chars < chunk_size_chars:
            raise ValueError(
                f"overlap ({overlap_chars}) must be smaller than chunk size "
                f"({chunk_size_chars})"
            )
        self._chunk_size = chunk_size_chars
        self._overlap = overlap_chars
        self._separators = tuple(separators)

    def split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        fragments = self._split_to_fit(text, self._separators)
        return self._merge_with_overlap(fragments)

    def _split_to_fit(self, text: str, separators: Sequence[str]) -> list[str]:
        """Break text into fragments no larger than the chunk budget.

        Tries the highest-order separator first; oversized fragments recurse
        with the remaining (finer-grained) separators. The final ``""``
        separator is a hard character cut — the last resort for pathological
        unbroken runs.
        """
        if len(text) <= self._chunk_size:
            return [text] if text else []
        if not separators or separators[0] == "":
            return [
                text[i : i + self._chunk_size]
                for i in range(0, len(text), self._chunk_size)
            ]
        separator, finer = separators[0], separators[1:]
        parts = text.split(separator)
        fragments: list[str] = []
        for i, part in enumerate(parts):
            # Re-attach the separator so numbering, sentence ends, and blank
            # lines survive into the chunk text verbatim.
            fragment = part + separator if i < len(parts) - 1 else part
            if not fragment:
                continue
            if len(fragment) <= self._chunk_size:
                fragments.append(fragment)
            else:
                fragments.extend(self._split_to_fit(fragment, finer))
        return fragments

    def _merge_with_overlap(self, fragments: list[str]) -> list[str]:
        """Greedily pack fragments into chunks, seeding each new chunk with
        the trailing fragments of the previous one (up to the overlap budget)."""
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        for fragment in fragments:
            if current and current_len + len(fragment) > self._chunk_size:
                chunks.append("".join(current))
                tail: list[str] = []
                tail_len = 0
                for prev in reversed(current):
                    if tail_len + len(prev) > self._overlap:
                        break
                    tail.insert(0, prev)
                    tail_len += len(prev)
                current, current_len = tail, tail_len
            current.append(fragment)
            current_len += len(fragment)
        if current:
            chunks.append("".join(current))
        return [chunk.strip() for chunk in chunks if chunk.strip()]
