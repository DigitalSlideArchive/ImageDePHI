import importlib.resources
from typing import Any

import yaml


def _load_profile(file_name: str) -> dict:
    with (importlib.resources.files("imagedephi") / file_name).open() as stream:
        return yaml.safe_load(stream)


def _profile_differences(base: Any, other: Any, path: str = "") -> list[str]:
    """List places where the modify dates profile deviates from the base profile."""
    if isinstance(base, dict) and isinstance(other, dict):
        differences = [f"{path}/{key}: only in base rules" for key in base.keys() - other.keys()]
        differences += [
            f"{path}/{key}: only in modify dates rules" for key in other.keys() - base.keys()
        ]
        for key in base.keys() & other.keys():
            differences += _profile_differences(base[key], other[key], f"{path}/{key}")
        return differences
    if base == other or (path.endswith("/action") and other == "modify_date"):
        return []
    return [f"{path}: {base!r} != {other!r}"]


def test_modify_dates_profile_matches_base_profile():
    base = _load_profile("base_rules.yaml")
    modify_dates = _load_profile("modify_dates_rules.yaml")
    for key in ("name", "description"):
        base.pop(key)
        modify_dates.pop(key)

    assert sorted(_profile_differences(base, modify_dates)) == []
