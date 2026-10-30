from dataclasses import dataclass, field


@dataclass(frozen=True)
class DogRef:
    """One dog to check. `key` must be unique and stable (e.g. "Rüden/benny")."""
    key: str
    name: str
    url: str
    folder: str = ""   # local folder of the dog (used by the photo checks later)


@dataclass(frozen=True)
class Finding:
    """kind: description | price | baseline | error"""
    dog: DogRef
    kind: str
    detail: str = ""


@dataclass
class RunResult:
    findings: list = field(default_factory=list)   # description / price changes
    checked: int = 0
    baselined: int = 0                              # dogs seen for the first time
    errors: list = field(default_factory=list)      # Finding(kind="error")
