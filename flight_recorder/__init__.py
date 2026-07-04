"""DAG-based flight recorder and local replay system for AI agents (MVP)."""

from .dag import validate_trace, verify_hashes
from .errors import (
    FinalOutputMismatch,
    FinalOutputNotCalled,
    FlightRecorderError,
    LifecycleError,
    PrematureEventError,
    ReplayDivergence,
    SchedulingError,
)
from .events import (
    BOUNDARY_EVENT_TYPES,
    EVENT_FIELDS,
    EVENT_TYPES,
    RECORDER_VERSION,
    SCHEMA_VERSION,
    STATUSES,
    TraceEvent,
)
from .hashing import argument_hash, canonical_json, context_hash, validate_json_value
from .recorder import Recorder
from .replayer import DagScheduler, Replayer, ReplayedError, TopologicalReplayer
from .report import ReplayReport, TraceValidationReport
from .storage import TraceWriter, TruncatedTraceWarning, read_events

__all__ = [
    "BOUNDARY_EVENT_TYPES",
    "DagScheduler",
    "EVENT_FIELDS",
    "EVENT_TYPES",
    "FinalOutputMismatch",
    "FinalOutputNotCalled",
    "FlightRecorderError",
    "LifecycleError",
    "PrematureEventError",
    "RECORDER_VERSION",
    "Recorder",
    "ReplayDivergence",
    "ReplayedError",
    "Replayer",
    "ReplayReport",
    "SCHEMA_VERSION",
    "STATUSES",
    "SchedulingError",
    "TopologicalReplayer",
    "TraceEvent",
    "TraceValidationReport",
    "TraceWriter",
    "TruncatedTraceWarning",
    "argument_hash",
    "canonical_json",
    "context_hash",
    "read_events",
    "validate_json_value",
    "validate_trace",
    "verify_hashes",
]
