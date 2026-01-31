from collections import OrderedDict

from shconfparser import Parser, TreeParseResult


class TreeBuildError(Exception):
    """Raised when input data is invalid or processing failed."""


def _replace_empty_strings_inplace(d):
    """Recursively replace all empty string values with empty OrderedDicts."""
    for k, v in d.items():
        if v == "":
            d[k] = OrderedDict()
        elif isinstance(v, dict):
            _replace_empty_strings_inplace(v)


def build_tree(multiline_text: str):
    """Parse multiline text into nested dictionary structure."""
    if not multiline_text.strip():
        msg = "Input text is empty"
        raise TreeBuildError(msg)

    lines = multiline_text.splitlines()
    parser = Parser()

    result: TreeParseResult = parser.parse_tree_safe(lines)

    if not result.success or result.data is None:
        msg = "No valid data or processing failed"
        raise TreeBuildError(msg)

    tree = result.data
    _replace_empty_strings_inplace(tree)
    return tree
