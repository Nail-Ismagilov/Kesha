"""Run the checks over a list of dogs. Still sequential (speed comes in step 4)."""
from . import http
from .checks import DEFAULT_CHECKS
from .context import Context
from .models import Finding, RunResult
from .page import parse_page


def run(dogs, store, checks=DEFAULT_CHECKS, on_progress=None, fetch=http.get_html,
        head_size=http.head_size, get_bytes=http.get_bytes):
    """Check every dog; never raises for a single dog (it becomes an error).

    on_progress(done, total) is called after each dog.
    """
    ctx = Context(store=store, fetch_html=fetch, head_size=head_size, get_bytes=get_bytes)
    result = RunResult()
    total = len(dogs)
    for i, dog in enumerate(dogs, start=1):
        try:
            page = parse_page(ctx.fetch_html(dog.url))   # one fetch + one parse per dog
            for check in checks:
                for f in check(dog, page, ctx):
                    if f.kind == "baseline":
                        result.baselined += 1
                    elif f.kind == "warning":
                        result.warnings.append(f)
                    else:
                        result.findings.append(f)
            result.checked += 1
        except Exception as e:                    # noqa: one bad page must not stop the run
            result.errors.append(Finding(dog, "error", str(e)))
        if on_progress:
            on_progress(i, total)
    return result
