"""A check is a function (dog, page, ctx) -> list[Finding]."""
from .description import check_description
from .first_photo import check_first_photo
from .photo_count import check_photo_count

DEFAULT_CHECKS = (check_description, check_first_photo, check_photo_count)
