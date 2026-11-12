"""Typed error taxonomy shared by the CLI, orchestration, and component seams."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class TerminalState(str, Enum):
    DONE_VALID = "DONE_VALID"
    DONE_INVALID = "DONE_INVALID"
    DONE_RESOLVED = "DONE_RESOLVED"
    DONE_UNRESOLVED = "DONE_UNRESOLVED"
    ERROR = "ERROR"


class TaxonomyCode(str, Enum):
    F2P_NOT_FAILING = "F2P_NOT_FAILING"
    P2P_NOT_PASSING = "P2P_NOT_PASSING"
    GOLDEN_NOT_APPLYING = "GOLDEN_NOT_APPLYING"
    GOLDEN_TESTS_FAILING = "GOLDEN_TESTS_FAILING"
    PARSER_UNKNOWN = "PARSER_UNKNOWN"
    TEST_EXEC_FAILED = "TEST_EXEC_FAILED"
    HIDDEN_STAGE_FAILED = "HIDDEN_STAGE_FAILED"
    NO_PATCH = "no_patch"
    PATCH_APPLY_FAILED = "patch_apply_failed"
    BUILD_FAILED = "build_failed"
    SOLVER_TIMEOUT = "solver_timeout"
    HIDDEN_TEST_FAILED = "hidden_test_failed"
    PARTIAL = "partial"
    REGRESSION = "regression"
    MIXED = "mixed"
    IMAGE_UNAVAILABLE = "IMAGE_UNAVAILABLE"
    PROVISION_FAILED = "PROVISION_FAILED"
    BASE_CHECKOUT_FAILED = "BASE_CHECKOUT_FAILED"
    SEAL_FAILED = "SEAL_FAILED"
    SOLVER_CRASHED = "SOLVER_CRASHED"
    BOUNDARY_VIOLATION = "BOUNDARY_VIOLATION"
    UNEXPECTED = "UNEXPECTED"


class BundleErrorCode(str, Enum):
    BUNDLE_INCOMPLETE = "BUNDLE_INCOMPLETE"
    BUNDLE_MALFORMED = "BUNDLE_MALFORMED"
    BUNDLE_INVALID = "BUNDLE_INVALID"
    BUNDLE_INCONSISTENT = "BUNDLE_INCONSISTENT"


class BundleInitErrorCode(str, Enum):
    INIT_REFUSED = "INIT_REFUSED"
    ROW_INCOMPLETE = "ROW_INCOMPLETE"
    ROW_MALFORMED = "ROW_MALFORMED"


class ContainerErrorCode(str, Enum):
    IMAGE_UNAVAILABLE = "IMAGE_UNAVAILABLE"
    PROVISION_FAILED = "PROVISION_FAILED"
    EXEC_FAILED = "EXEC_FAILED"
    COPY_FAILED = "COPY_FAILED"
    DESTROY_FAILED = "DESTROY_FAILED"


class StoreNotFoundError(Exception):
    """Raised when a requested persisted run does not exist."""


class CodedError(Exception):
    """Base exception carrying a stable machine-readable code."""

    code: Enum

    def __init__(self, message: str = "", *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__
        self.details = dict(details or {})

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"


class BundleError(CodedError):
    code = BundleErrorCode.BUNDLE_MALFORMED


class BundleIncompleteError(BundleError):
    code = BundleErrorCode.BUNDLE_INCOMPLETE


class BundleMalformedError(BundleError):
    code = BundleErrorCode.BUNDLE_MALFORMED


class BundleInvalidError(BundleError):
    code = BundleErrorCode.BUNDLE_INVALID


class BundleInconsistentError(BundleError):
    code = BundleErrorCode.BUNDLE_INCONSISTENT


class BundleInitError(BundleError):
    code = BundleInitErrorCode.ROW_MALFORMED


class InitRefusedError(BundleInitError):
    code = BundleInitErrorCode.INIT_REFUSED


class RowIncompleteError(BundleInitError):
    code = BundleInitErrorCode.ROW_INCOMPLETE


class RowMalformedError(BundleInitError):
    code = BundleInitErrorCode.ROW_MALFORMED


class ContainerError(CodedError):
    code = ContainerErrorCode.EXEC_FAILED


class ImageUnavailableError(ContainerError):
    code = ContainerErrorCode.IMAGE_UNAVAILABLE


class ProvisionFailedError(ContainerError):
    code = ContainerErrorCode.PROVISION_FAILED


class ExecFailedError(ContainerError):
    code = ContainerErrorCode.EXEC_FAILED


class CopyFailedError(ContainerError):
    code = ContainerErrorCode.COPY_FAILED


class DestroyFailedError(ContainerError):
    code = ContainerErrorCode.DESTROY_FAILED


@dataclass(frozen=True)
class PhaseError(Exception):
    """State-machine failure that maps directly to a terminal verdict."""

    terminal_state: TerminalState
    taxonomy_code: TaxonomyCode
    message_template: str
    context: Mapping[str, Any] | None = None

    @property
    def terminal(self) -> Any:
        return self.terminal_state

    @property
    def code(self) -> str:
        return self.taxonomy_code.value if isinstance(self.taxonomy_code, Enum) else str(self.taxonomy_code)

    def render(self, ctx: Any | None = None) -> str:
        values = dict(self.context or {})
        if ctx is not None:
            values.update(getattr(ctx, "__dict__", {}))
        try:
            message = self.message_template.format(**values)
        except KeyError:
            message = self.message_template
        terminal = self.terminal_state.value if isinstance(self.terminal_state, Enum) else str(self.terminal_state)
        return f"{terminal}: {self.code}: {message}"

    def __str__(self) -> str:
        return self.render()
