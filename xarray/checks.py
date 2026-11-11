"""Inputs for the xarray where() replay. Each check runs independently."""
import contextlib
import io
import json
from pathlib import Path
import sys

import xarray as xr
from xarray.testing import assert_identical


def first_input():
    """Pranav Lakhwara, before the closing notes."""
    cond = xr.DataArray([1, 2, 3], attrs={"from": "cond"}) > 0
    result = xr.where(cond, 1, 0, keep_attrs=True)

    print(result.values)  # [1 1 1]
    print(result.attrs)   # {}


def added_assertion():
    """Pranav Lakhwara, after the closing notes and before seeing results."""
    cond = xr.DataArray([True, True, True], attrs={"source": "cond"})
    result = xr.where(cond, 1, 0, keep_attrs=True)

    assert result.attrs == {}


def reviewer_1():
    """Model reviewer with notes, A then B."""
    cond = xr.DataArray([True, False], dims="i", attrs={"source": "condition"})
    for y in (0, xr.DataArray([0, 0], dims="i", attrs={"source": "y"})):
        result = xr.where(cond, 1, y, keep_attrs=True)
        assert result.values.tolist() == [1, 0]
        assert result.attrs == {}, (type(y).__name__, result.attrs)


def reviewer_2():
    """Model reviewer with notes, B then A."""
    cond = xr.DataArray([True, False], dims="i", attrs={"source": "condition"})
    y = xr.DataArray([20, 30], dims="i", attrs={"source": "y"})

    result = xr.where(cond, 1, y, keep_attrs=True)

    assert result.values.tolist() == [1, 30]
    assert result.attrs == {}


def reviewer_3():
    """Model reviewer without notes, A then B."""
    cond = xr.DataArray([True, False], dims="n", attrs={"source": "cond"})
    for y in (0, xr.DataArray([8, 0], dims="n", attrs={"source": "y"})):
        result = xr.where(cond, 1, y, keep_attrs=True)
        assert result.values.tolist() == [1, 0]
        assert result.attrs == {}, (type(y).__name__, result.attrs)


def reviewer_4():
    """Model reviewer without notes, B then A."""
    cond = xr.DataArray([True, False], attrs={"source": "condition"})
    for y in (0, xr.DataArray([0, 0], attrs={"source": "y"})):
        result = xr.where(cond, 1, y, keep_attrs=True)
        assert result.values.tolist() == [1, 0]
        assert result.attrs == {}, result.attrs


def test_where_attrs() -> None:
    cond = xr.DataArray([True, False], dims="x", attrs={"attr": "cond"})
    x = xr.DataArray([1, 1], dims="x", attrs={"attr": "x"})
    y = xr.DataArray([0, 0], dims="x", attrs={"attr": "y"})
    actual = xr.where(cond, x, y, keep_attrs=True)
    expected = xr.DataArray([1, 0], dims="x", attrs={"attr": "x"})
    assert_identical(expected, actual)

    # ensure keep_attrs can handle scalar values
    actual = xr.where(cond, 1, 0, keep_attrs=True)
    assert actual.attrs == {}


def original_diagnostic():
    """Codex diagnostic recorded after the human proposed both checks."""
    conditions = (
        ("first", xr.DataArray([1, 2, 3], attrs={"from": "cond"}) > 0),
        ("second", xr.DataArray([True, True, True], attrs={"source": "cond"})),
    )
    for label, condition in conditions:
        print(label, "condition attrs", dict(condition.attrs))
        try:
            result = xr.where(condition, 1, 0, keep_attrs=True)
            print(label, "values", result.values.tolist(), "result attrs", dict(result.attrs))
        except Exception as error:
            print(label, type(error).__name__, str(error))


def followup_diagnostic():
    """Codex diagnostic showing each branch, even when the first one fails."""
    cond = xr.DataArray([True, False], dims="i", attrs={"source": "condition"})
    for y in (0, xr.DataArray([20, 30], dims="i", attrs={"source": "y"})):
        try:
            result = xr.where(cond, 1, y, keep_attrs=True)
            print(type(y).__name__, result.values.tolist(), result.attrs)
        except Exception as error:
            print(type(y).__name__, type(error).__name__, str(error))


def run(version):
    checks = [first_input, added_assertion]
    # The initial diagnostic was recorded for these three versions only.
    if version != "maintainer":
        checks.append(original_diagnostic)
    checks.extend([test_where_attrs, reviewer_1, reviewer_2, reviewer_3, reviewer_4, followup_diagnostic])
    for check in checks:
        output = io.StringIO()
        error_message = ""
        with contextlib.redirect_stdout(output):
            try:
                check()
            except Exception as error:
                error_message = type(error).__name__
                if str(error):
                    error_message += ": " + str(error)
        print("\t".join((version, check.__name__, json.dumps(output.getvalue()), error_message or "OK")))


if __name__ == "__main__":
    version, source = sys.argv[1:]
    if Path(xr.__file__).resolve() != Path(source).resolve() / "xarray" / "__init__.py":
        sys.exit("Could not import the selected source tree.")
    run(version)
