"""Everything a check may use besides the dog and its parsed page.

Checks get ONE object instead of many arguments, and tests can replace the
network functions with fakes.
"""
from dataclasses import dataclass, field
from typing import Callable

from . import http
from .store import Store


@dataclass
class Context:
    store: Store
    fetch_html: Callable = http.get_html
    head_size: Callable = http.head_size
    get_bytes: Callable = http.get_bytes
