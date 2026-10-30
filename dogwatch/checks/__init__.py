"""A check is a function (dog, page, ctx) -> list[Finding]."""
from .description import check_description
from .first_photo import check_first_photo

DEFAULT_CHECKS = (check_description, check_first_photo)
