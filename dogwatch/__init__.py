"""dogwatch - detect changes of dogs on the shelter website.

Standalone package: it does not import the GUI or any other module of the
main application. The host app passes in a list of DogRef objects and gets
Finding objects back.
"""
from .models import DogRef, Finding, RunResult
from .runner import run
from .store import Store

__all__ = ["DogRef", "Finding", "RunResult", "Store", "run"]
