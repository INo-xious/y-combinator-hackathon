"""JSONL trace storage: append-with-flush writing, partial-line-tolerant reading.

One event per line (PLAN §5). The writer validates every event before it is
serialized — bad traces are never written — and flushes after every line, so
a crash leaves at most one incomplete final line (PLAN §2). The reader
tolerates exactly that: an unparseable *final* line is warned about and
skipped; anything else wrong in the file is corruption and raises (PLAN §8).

Trace-level invariants (metadata first, DAG shape, lifecycle) are not checked
here — see ``dag.py``.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Union

from .events import TraceEvent


class TruncatedTraceWarning(UserWarning):
    """The final trace line was incomplete (crash-interrupted write) and was skipped."""


class TraceWriter:
    """Append-only JSONL writer for one trace file.

    Refuses to touch an existing file unless ``overwrite=True``, in which
    case the file is truncated and started fresh (PLAN §2).
    """

    def __init__(self, path: Union[str, Path], overwrite: bool = False):
        self._path = Path(path)
        # "x" makes the existence check and the create one atomic operation.
        mode = "w" if overwrite else "x"
        self._file = self._path.open(mode, encoding="utf-8", newline="\n")

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: TraceEvent) -> None:
        """Validate *event*, write it as one JSON line, and flush."""
        event.validate()
        line = json.dumps(event.to_dict(), ensure_ascii=False, allow_nan=False)
        self._file.write(line + "\n")
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False


def read_events(path: Union[str, Path]) -> list[TraceEvent]:
    """Read and per-event-validate every event in a JSONL trace file.

    Recovery rule: if the *final* line does not parse as JSON it is treated
    as a crash-truncated write — a ``TruncatedTraceWarning`` is emitted and
    the events before it are returned. An unparseable line anywhere else, or
    a line that parses but is not a valid event, raises ``ValueError``.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if text == "":
        return []
    lines = text.split("\n")
    if lines[-1] == "":  # complete file: final line ended with "\n"
        lines.pop()
    events: list[TraceEvent] = []
    last = len(lines) - 1
    for index, line in enumerate(lines):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            if index == last:
                warnings.warn(
                    f"{path}: final line {index + 1} is incomplete "
                    "(crash-interrupted write); skipping it",
                    TruncatedTraceWarning,
                    stacklevel=2,
                )
                break
            raise ValueError(
                f"corrupt trace {path}: line {index + 1} is not valid JSON"
            ) from None
        try:
            events.append(TraceEvent.from_dict(data))
        except ValueError as exc:
            raise ValueError(f"corrupt trace {path}: line {index + 1}: {exc}") from exc
    return events
