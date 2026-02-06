import inspect
from lifeos.canon import read_gate


ALLOWED_PUBLIC_READ_FUNCTIONS = {
    "load_canon_json",
    "load_strategy_json",
    "load_tree_json",
}


def test_explicit_canon_read_api_surface():
    """
    Canon read surface must be explicit.
    No new public read helpers may be introduced without governance.
    """

    public_functions = {
        name
        for name, obj in inspect.getmembers(read_gate)
        if inspect.isfunction(obj) and not name.startswith("_")
    }

    unexpected = public_functions - ALLOWED_PUBLIC_READ_FUNCTIONS

    if unexpected:
        raise AssertionError(
            f"Unauthorized Canon read functions detected: {sorted(unexpected)}"
        )