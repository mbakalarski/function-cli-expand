from collections import OrderedDict

from shconfparser import Parser


class TreeBuildError(Exception):
    """Raised when input data is invalid or processing failed."""

    pass


def _replace_empty_strings_inplace(d):
    """Recursively replace all empty string values ('') with empty dicts ({})."""
    for k, v in d.items():
        if v == "":
            d[k] = {}
        elif isinstance(v, dict):
            _replace_empty_strings_inplace(v)


def build_tree(multiline_text: str) -> OrderedDict:
    """Parse multiline text into nested dictionary structure."""
    lines = multiline_text.splitlines()

    p = Parser()
    tree_parse_result = p.parse_tree_safe(lines)

    if tree_parse_result.success:
        tree = tree_parse_result.data
    else:
        err_msg = "No valid data or processing failed"
        raise TreeBuildError(err_msg)

    _replace_empty_strings_inplace(tree)

    return OrderedDict(tree)
