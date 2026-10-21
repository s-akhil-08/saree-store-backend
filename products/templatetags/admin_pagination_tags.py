from django import template
from myproject.admin_pagination import (
    get_smart_pagination_range,
    get_record_range,
    ALLOWED_PAGE_SIZES,
    DEFAULT_PAGE_SIZE,
)

register = template.Library()


@register.simple_tag
def get_admin_pagination_range(cl):
    """Returns smart pagination range with ellipsis for the changelist."""
    if not hasattr(cl, "paginator") or not cl.paginator:
        return [1]
    return get_smart_pagination_range(cl.page_num, cl.paginator.num_pages)


@register.simple_tag
def get_admin_start_index(cl):
    """Calculates start record index for current page."""
    start, _ = get_record_range(cl)
    return start


@register.simple_tag
def get_admin_end_index(cl):
    """Calculates end record index for current page."""
    _, end = get_record_range(cl)
    return end


@register.simple_tag
def get_admin_page_url(cl, page_num):
    """Generates URL preserving all active filters and setting page number."""
    try:
        p_num = int(page_num)
    except (ValueError, TypeError):
        p_num = 1
    # Django ChangeList uses PAGE_VAR = 'p'
    return cl.get_query_string({"p": p_num})


@register.simple_tag
def get_admin_page_size_url(cl, page_size):
    """Generates URL preserving all active filters, updating page_size, and resetting to page 1."""
    try:
        size = int(page_size)
    except (ValueError, TypeError):
        size = DEFAULT_PAGE_SIZE
    # Setting page_size and resetting to page 1
    return cl.get_query_string({"page_size": size, "p": 1})


@register.simple_tag
def get_page_size_options():
    """Returns list of selectable page size options."""
    return list(ALLOWED_PAGE_SIZES)
