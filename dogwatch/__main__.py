"""python -m dogwatch run --dogs dogs.json [--db dogwatch.db]
   python -m dogwatch check URL [--name NAME] [--folder DIR] [--db dogwatch.db]

dogs.json: [{"key": "Rüden/benny", "name": "benny", "url": "https://...", "folder": "C:/dogs/Rüden/benny"}, ...]
"""
import argparse
import json
import sys

from .models import DogRef
from .runner import run
from .store import Store


def _print(result):
    for f in result.findings:
        print(f"[{f.kind}] {f.dog.key}: {f.detail}")
    for f in result.warnings:
        print(f"[warning] {f.dog.key}: {f.detail}")
    for f in result.errors:
        print(f"[error] {f.dog.key}: {f.detail}")
    print(f"checked={result.checked} baseline={result.baselined} "
          f"changes={len(result.findings)} warnings={len(result.warnings)} "
          f"errors={len(result.errors)}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dogwatch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="check all dogs of a JSON file")
    p_run.add_argument("--dogs", required=True)
    p_run.add_argument("--db", default="dogwatch.db")
    p_chk = sub.add_parser("check", help="check one dog page")
    p_chk.add_argument("url")
    p_chk.add_argument("--name", default=None)
    p_chk.add_argument("--folder", default="", help="local dog folder (enables the photo check)")
    p_chk.add_argument("--db", default="dogwatch.db")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        with open(args.dogs, encoding="utf-8") as f:
            dogs = [DogRef(**d) for d in json.load(f)]
    else:
        name = args.name or args.url.rstrip("/").rsplit("/", 1)[-1]
        dogs = [DogRef(key=name, name=name, url=args.url, folder=args.folder)]

    store = Store(args.db)
    try:
        _print(run(dogs, store, on_progress=lambda d, t: print(f"  {d}/{t}", file=sys.stderr)))
    finally:
        store.close()


if __name__ == "__main__":
    main()
