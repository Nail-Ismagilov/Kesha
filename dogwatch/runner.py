"""Run the checks over a list of dogs - concurrently, with a page cache.

Speed (the network is what is slow, not the CPU):
* a thread pool works on several dogs at once (default 6 workers);
* each dog costs ONE page request, sent with ETag / Last-Modified, so an
  unchanged page is answered with a tiny 304 and is not parsed again;
* the photo checks need only a HEAD request in the normal case.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from . import http
from .checks import DEFAULT_CHECKS
from .context import Context
from .models import Finding, RunResult
from .page import PageData, parse_page

DEFAULT_WORKERS = 6


@dataclass
class _Outcome:
    findings: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    baselined: int = 0
    from_cache: bool = False
    error: Finding = None


def _load_page(dog, ctx, use_cache):
    """Return (PageData, from_cache)."""
    cache = ctx.store.get_page_cache(dog.key) if use_cache else None
    fetched = ctx.fetch_page(dog.url,
                             cache["etag"] if cache else None,
                             cache["last_modified"] if cache else None)
    if fetched.status == 304:
        if cache is None:
            raise RuntimeError("server answered 304 without a cached copy")
        return PageData(cache["description"], cache["photo_urls"]), True
    page = parse_page(fetched.text)
    if use_cache and (fetched.etag or fetched.last_modified):
        ctx.store.put_page_cache(dog.key, fetched.etag, fetched.last_modified,
                                 page.description, page.photo_urls)
    return page, False


def _check_dog(dog, ctx, checks, use_cache):
    out = _Outcome()
    try:
        page, out.from_cache = _load_page(dog, ctx, use_cache)
        for check in checks:
            for f in check(dog, page, ctx):
                if f.kind == "baseline":
                    out.baselined += 1
                elif f.kind == "warning":
                    out.warnings.append(f)
                else:
                    out.findings.append(f)
    except Exception as e:                        # noqa: one bad dog must not stop the run
        out = _Outcome(error=Finding(dog, "error", str(e)))
    return out


def run(dogs, store, checks=DEFAULT_CHECKS, on_progress=None, workers=DEFAULT_WORKERS,
        use_cache=True, fetch=None, fetch_page=http.fetch_page,
        head_size=http.head_size, get_bytes=http.get_bytes):
    """Check every dog; never raises for a single dog (it becomes an error).

    on_progress(done, total) is called after each dog, from the calling thread.
    fetch(url) -> html is a simple replacement for fetch_page without caching.
    Findings are returned in the order of `dogs`, whatever order the threads finish in.
    """
    if fetch is not None:
        fetch_page = lambda url, etag=None, last_modified=None: http.Fetched(200, fetch(url))
    ctx = Context(store=store, fetch_page=fetch_page, head_size=head_size, get_bytes=get_bytes)
    dogs = list(dogs)
    total = len(dogs)
    outcomes = [None] * total
    started = time.monotonic()

    if workers <= 1 or total <= 1:
        for i, dog in enumerate(dogs):
            outcomes[i] = _check_dog(dog, ctx, checks, use_cache)
            if on_progress:
                on_progress(i + 1, total)
    else:
        with ThreadPoolExecutor(max_workers=min(workers, total)) as pool:
            futures = {pool.submit(_check_dog, dog, ctx, checks, use_cache): i
                       for i, dog in enumerate(dogs)}
            for done, fut in enumerate(as_completed(futures), start=1):
                outcomes[futures[fut]] = fut.result()
                if on_progress:
                    on_progress(done, total)

    result = RunResult()
    for out in outcomes:                          # input order -> deterministic output
        if out.error is not None:
            result.errors.append(out.error)
            continue
        result.checked += 1
        result.baselined += out.baselined
        result.cached += 1 if out.from_cache else 0
        result.findings.extend(out.findings)
        result.warnings.extend(out.warnings)
    result.seconds = time.monotonic() - started
    return result
