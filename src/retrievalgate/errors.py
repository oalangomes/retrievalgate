"""Domain-specific errors with stable CLI semantics."""


class RetrievalGateError(Exception):
    """Base error for expected retrievalgate failures."""


class ScenarioError(RetrievalGateError):
    """A scenario file is invalid or cannot be loaded."""


class AdapterError(RetrievalGateError):
    """An external retriever failed the command adapter contract."""
