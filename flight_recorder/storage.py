"""JSONL trace storage: append-with-flush writing, partial-line-tolerant reading.

One event per line (PLAN §5). The writer validates every event before it is
serialized — bad traces are never written — and flushes after every line, so
a crash leaves at most one incomplete final line (PLAN §2). The reader
tolerates exactly that: an unparseable *final* line is warned about and
skipped; anything else wrong in the file is corruption and raises (PLAN §8).

Trace-level invariants (metadata first, DAG shape, lifecycle) are not checked
here — see ``dag.py``.

Optional payload encryption (``crypto.py``) plugs in here as a storage-layer
transform: the writer encrypts ``payload``/``historical_response`` after the
plaintext event was validated, and the reader decrypts them before
``TraceEvent.from_dict`` — everything above storage sees plaintext.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Iterator, Optional, Union, Literal
from .crypto import Cipher, decrypt_event_fields, encrypt_event_fields, is_encrypted_event_dict
from .events import TraceEvent


class TruncatedTraceWarning(UserWarning):
    """The final trace line was incomplete (crash-interrupted write) and was skipped."""


class TraceWriter:
    """Append-only JSONL writer for one trace file.

    Refuses to touch an existing file unless ``overwrite=True``, in which
    case the file is truncated and started fresh (PLAN §2).
    """

    def __init__(
        self,
        path: Union[str, Path],
        overwrite: bool = False,
        cipher: Optional[Cipher] = None,
    ):
        self._path = Path(path)
        self._cipher = cipher
        # "x" makes the existence check and the create one atomic operation.
        mode = "w" if overwrite else "x"
        self._file = self._path.open(mode, encoding="utf-8", newline="\n")

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: TraceEvent) -> None:
        """Validate *event*, write it as one JSON line, and flush."""
        event.validate(validation_cache=getattr(event, "_validation_cache", None))
        data = event.to_json_dict()
        if self._cipher is not None:
            data = encrypt_event_fields(data, self._cipher)
        line = json.dumps(data, ensure_ascii=False, allow_nan=False)
        self._file.write(line + "\n")
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        self.close()
        return False


def iter_events(
    path: Union[str, Path],
    *,
    cipher: Optional[Cipher] = None,
) -> Iterator[TraceEvent]:
    """Yield per-event-validated events from a JSONL trace file.

    Recovery rule: if the *final* line does not parse as JSON it is treated
    as a crash-truncated write — a ``TruncatedTraceWarning`` is emitted and
    the events before it are returned. An unparseable line anywhere else, or
    a line that parses but is not a valid event, raises ``ValueError``.

    Encrypted traces need the matching *cipher*; reading one without it
    raises ``ValueError`` rather than yielding ciphertext.
    """
    path = Path(path)
    pending_line: str | None = None
    pending_line_number = 0
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if pending_line is not None:
                event = _event_from_line(
                    path, pending_line_number, pending_line, is_final=False, cipher=cipher
                )
                assert event is not None
                yield event
            pending_line = line
            pending_line_number = line_number
    if pending_line is not None:
        event = _event_from_line(
            path, pending_line_number, pending_line, is_final=True, cipher=cipher
        )
        if event is not None:
            yield event


def _event_from_line(
    path: Path,
    line_number: int,
    line: str,
    *,
    is_final: bool,
    cipher: Optional[Cipher] = None,
) -> TraceEvent | None:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        if is_final:
            warnings.warn(
                f"{path}: final line {line_number} is incomplete "
                "(crash-interrupted write); skipping it",
                TruncatedTraceWarning,
                stacklevel=2,
            )
            return None
        raise ValueError(
            f"corrupt trace {path}: line {line_number} is not valid JSON"
        ) from None
    if is_encrypted_event_dict(data):
        if cipher is None:
            raise ValueError(
                f"encrypted trace {path}: line {line_number} needs a cipher — "
                "pass cipher=... (or set AGENT_RR_ENCRYPTION_KEY for the CLI)"
            )
        try:
            data = decrypt_event_fields(data, cipher)
        except Exception as exc:
            raise ValueError(
                f"encrypted trace {path}: line {line_number} failed to decrypt "
                f"(wrong key?): {type(exc).__name__}: {exc}"
            ) from exc
    try:
        return TraceEvent.from_dict(data)
    except ValueError as exc:
        raise ValueError(f"corrupt trace {path}: line {line_number}: {exc}") from exc


def read_events(
    path: Union[str, Path],
    *,
    cipher: Optional[Cipher] = None,
) -> list[TraceEvent]:
    """Read and per-event-validate every event in a JSONL trace file."""
    return list(iter_events(path, cipher=cipher))
