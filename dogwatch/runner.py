"""Run the checks over a list of dogs. Step 1: sequential."""
from . import http
from .checks import DEFAULT_CHECKS
from .models import Finding, RunResult
from .page import parse_page


def run(dogs, store, checks=DEFAULT_CHECKS, on_progress=None, fetch=http.get_html):
    """Check every dog; never raises for a single dog (it becomes an error).

    on_progress(done, total) is called after each dog.
    """
    result = RunResult()
    total = len(dogs)
    for i, dog in enumerate(dogs, start=1):
        try:
            page = parse_page(fetch(dog.url))     # one fetch + one parse per dog
            for check in checks:
                for f in check(dog, page, store):
                    if f.kind == "baseline":
                        result.baselined += 1
                    else:
                        result.findings.append(f)
            result.checked += 1
        except Exception as e:                    # noqa: one bad page must not stop the run
            result.errors.append(Finding(dog, "error", str(e)))
        if on_progress:
            on_progress(i, total)
    return result
