from dataclasses import dataclass, field


@dataclass(frozen=True)
class DogRef:
    """One dog to check.

    key     unique and stable (e.g. "Rüden/benny")
    name    the dog's name as used for its files: photo n is <folder>/<name>n.jpg
    url     detail page
    folder  local folder of the dog; the photo checks are skipped if empty
    """
    key: str
    name: str
    url: str
    folder: str = ""


@dataclass(frozen=True)
class Finding:
    """kind: description | price | first_photo | photo_count | baseline | warning | error"""
    dog: DogRef
    kind: str
    detail: str = ""


@dataclass
class RunResult:
    findings: list = field(default_factory=list)   # real changes, in input order
    checked: int = 0
    baselined: int = 0                              # dogs seen for the first time
    cached: int = 0                                 # detail pages answered with 304
    seconds: float = 0.0                            # wall-clock time of the run
    warnings: list = field(default_factory=list)    # a check could not decide (Finding)
    errors: list = field(default_factory=list)      # a dog could not be checked (Finding)
