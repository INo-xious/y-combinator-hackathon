"""DAG-based flight recorder and local replay system for AI agents (MVP)."""

from .crypto import Cipher, load_fernet_cipher
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
from .hashing import (
    FLOAT_POLICIES,
    FLOAT_POLICY_ALLOW,
    FLOAT_POLICY_REJECT,
    argument_hash,
    canonical_json,
    context_hash,
    float_hex,
    validate_json_value,
)
from .loops import LoopRun, LoopStep
from .recorder import Recorder
from .replayer import (
    DagScheduler,
    Replayer,
    ReplayedError,
    TopologicalReplayer,
    REPLAY_MODE_SEMANTIC,
    REPLAY_MODE_STRICT,
    REPLAY_MODE_STRUCTURED,
    REPLAY_MODES,
)
from .report import ReplayReport, TraceValidationReport
from .signing import resolve_signing_key, sign_event, verify_signatures
from .storage import TraceWriter, TruncatedTraceWarning, iter_events, read_events

__all__ = [
    "BOUNDARY_EVENT_TYPES",
    "Cipher",
    "DagScheduler",
    "EVENT_FIELDS",
    "EVENT_TYPES",
    "FLOAT_POLICIES",
    "FLOAT_POLICY_ALLOW",
    "FLOAT_POLICY_REJECT",
    "FinalOutputMismatch",
    "FinalOutputNotCalled",
    "FlightRecorderError",
    "LifecycleError",
    "LoopRun",
    "LoopStep",
    "PrematureEventError",
    "RECORDER_VERSION",
    "REPLAY_MODE_SEMANTIC",
    "REPLAY_MODE_STRICT",
    "REPLAY_MODE_STRUCTURED",
    "REPLAY_MODES",
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
    "float_hex",
    "iter_events",
    "load_fernet_cipher",
    "read_events",
    "resolve_signing_key",
    "sign_event",
    "validate_json_value",
    "verify_signatures",
    "validate_trace",
    "verify_hashes",
]
