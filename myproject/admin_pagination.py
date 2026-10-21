"""
Dynamic Scalable Pagination for Django Admin
Provides server-side dynamic pagination, configurable page sizes (12, 24, 48, 96),
session persistence, and smart range computation matching the frontend design system.
"""

from typing import List, Union, Tuple
from django.contrib.admin.views import main

PAGE_SIZE_PARAM = "page_size"
PER_PAGE_PARAM = "per_page"
DEFAULT_PAGE_SIZE = 24
ALLOWED_PAGE_SIZES = (12, 24, 48, 96)

# 1. Register page_size and per_page into Django Admin's IGNORED_PARAMS
# so ChangeList never treats them as database filter field lookups.
if PAGE_SIZE_PARAM not in main.IGNORED_PARAMS:
    main.IGNORED_PARAMS = tuple(list(main.IGNORED_PARAMS) + [PAGE_SIZE_PARAM, PER_PAGE_PARAM])


# 2. Hook ChangeList.__init__ to support dynamic server-side page size across ALL models
_original_changelist_init = main.ChangeList.__init__

def _dynamic_changelist_init(self, request, *args, **kwargs):
    # Determine requested page size from URL query string or session
    page_size = None
    raw_size = request.GET.get(PAGE_SIZE_PARAM) or request.GET.get(PER_PAGE_PARAM)

    if raw_size:
        try:
            val = int(raw_size)
            if 1 <= val <= 500:
                page_size = val
                # Persist user preference in session across admin sections
                if hasattr(request, "session"):
                    request.session["admin_page_size"] = val
        except (ValueError, TypeError):
            pass

    if not page_size and hasattr(request, "session"):
        val = request.session.get("admin_page_size")
        if isinstance(val, int) and 1 <= val <= 500:
            page_size = val

    if not page_size:
        page_size = DEFAULT_PAGE_SIZE

    # Inject page_size into kwargs or args (position 7 is list_per_page in ChangeList.__init__)
    if "list_per_page" in kwargs:
        kwargs["list_per_page"] = page_size
    elif len(args) >= 8:
        args_list = list(args)
        args_list[7] = page_size
        args = tuple(args_list)

    _original_changelist_init(self, request, *args, **kwargs)
    self.list_per_page = page_size

main.ChangeList.__init__ = _dynamic_changelist_init


def get_smart_pagination_range(current_page: int, total_pages: int, delta: int = 1) -> List[Union[int, str]]:
    """
    Computes a smart pagination range with ellipsis (...) matching the frontend design:
    e.g. [1, 2, 3, '...', 20] or [1, '...', 4, 5, 6, '...', 20]
    """
    if total_pages <= 7:
        return list(range(1, total_pages + 1))

    range_list: List[Union[int, str]] = []
    start = max(2, current_page - delta)
    end = min(total_pages - 1, current_page + delta)

    for p in range(start, end + 1):
        range_list.append(p)

    if current_page - delta > 2:
        range_list.insert(0, "...")
    if current_page + delta < total_pages - 1:
        range_list.append("...")

    range_list.insert(0, 1)
    if total_pages > 1:
        range_list.append(total_pages)

    return range_list


def get_record_range(cl) -> Tuple[int, int]:
    """
    Calculates start and end item index for current page:
    e.g. (1, 24) or (25, 48)
    """
    total = getattr(cl, "result_count", 0)
    if total == 0:
        return 0, 0
    per_page = getattr(cl.paginator, "per_page", DEFAULT_PAGE_SIZE)
    current_page = getattr(cl, "page_num", 1)
    start = (current_page - 1) * per_page + 1
    end = min(total, current_page * per_page)
    return start, end
