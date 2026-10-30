"""A check is a function (dog, page, store) -> list[Finding]."""
from .description import check_description

DEFAULT_CHECKS = (check_description,)
