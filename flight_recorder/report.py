"""Report structures for replay and trace validation (PLAN §3, CLI spec).

Plain data holders: the Replayer fills a :class:`ReplayReport` as it consumes
events; the CLI ``validate`` command produces a :class:`TraceValidationReport`.
``to_dict`` shapes match the machine-readable CLI output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TraceValidationReport:
    """Outcome of full-trace validation: schema, DAG invariant, lifecycle
    invariants, and hash re-verification."""

    valid: bool
    events: int
    hashes_verified: bool
    errors: list[str] = field(default_factory=list)
    # None means signature verification was not attempted (no signing key);
    # omitted from to_dict in that case so unsigned output is unchanged.
    signatures_verified: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        if self.valid:
            payload = {
                "status": "valid",
                "events": self.events,
                "hashes_verified": self.hashes_verified,
            }
            if self.signatures_verified is not None:
                payload["signatures_verified"] = self.signatures_verified
            return payload
        return {"status": "invalid", "errors": list(self.errors)}


@dataclass
class ReplayReport:
    """Outcome of one replay run: what matched, what was never consumed,
    how the run diverged (if it did), and the final-output comparison.

    ``final_output_matched`` is ``None`` until ``record_final_output`` runs.
    ``divergence`` holds :meth:`ReplayDivergence.detail` output.
    """

    run_id: Optional[str] = None
    matched_event_ids: list[str] = field(default_factory=list)
    unconsumed_event_ids: list[str] = field(default_factory=list)
    divergence: Optional[dict] = None
    final_output_matched: Optional[bool] = None

    @property
    def clean(self) -> bool:
        """True when every event matched, nothing was left over, and the
        final output compared equal."""
        return (
            self.divergence is None
            and not self.unconsumed_event_ids
            and self.final_output_matched is True
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "matched_events": len(self.matched_event_ids),
            "matched_event_ids": list(self.matched_event_ids),
            "unconsumed_event_ids": list(self.unconsumed_event_ids),
            "divergence": self.divergence,
            "final_output_matched": self.final_output_matched,
            "clean": self.clean,
        }
