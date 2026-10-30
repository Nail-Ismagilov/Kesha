"""python -m dogwatch run --dogs dogs.json [--db dogwatch.db] [--workers 6] [--no-cache]
   python -m dogwatch check URL [--name NAME] [--folder DIR] [--db dogwatch.db]

dogs.json: [{"key": "Rüden/benny", "name": "benny", "url": "https://...", "folder": "C:/dogs/Rüden/benny"}, ...]
"""
import argparse
import json
import sys

from .models import DogRef
from .runner import DEFAULT_WORKERS, run
from .store import Store


def _print(result):
    for f in result.findings:
        print(f"[{f.kind}] {f.dog.key}: {f.detail}")
    for f in result.warnings:
        print(f"[warning] {f.dog.key}: {f.detail}")
    for f in result.errors:
        print(f"[error] {f.dog.key}: {f.detail}")
    print(f"checked={result.checked} baseline={result.baselined} cached={result.cached} "
          f"changes={len(result.findings)} warnings={len(result.warnings)} "
          f"errors={len(result.errors)} time={result.seconds:.1f}s")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dogwatch")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--db", default="dogwatch.db")
        p.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                       help="parallel requests (1 = sequential)")
        p.add_argument("--no-cache", action="store_true",
                       help="do not send ETag/If-Modified-Since")

    p_run = sub.add_parser("run", help="check all dogs of a JSON file")
    p_run.add_argument("--dogs", required=True)
    common(p_run)
    p_chk = sub.add_parser("check", help="check one dog page")
    p_chk.add_argument("url")
    p_chk.add_argument("--name", default=None)
    p_chk.add_argument("--folder", default="", help="local dog folder (enables the photo checks)")
    common(p_chk)
    args = ap.parse_args(argv)

    if args.cmd == "run":
        with open(args.dogs, encoding="utf-8") as f:
            dogs = [DogRef(**d) for d in json.load(f)]
    else:
        name = args.name or args.url.rstrip("/").rsplit("/", 1)[-1]
        dogs = [DogRef(key=name, name=name, url=args.url, folder=args.folder)]

    store = Store(args.db)
    try:
        _print(run(dogs, store, workers=args.workers, use_cache=not args.no_cache,
                   on_progress=lambda d, t: print(f"  {d}/{t}", file=sys.stderr)))
    finally:
        store.close()


if __name__ == "__main__":
    main()
