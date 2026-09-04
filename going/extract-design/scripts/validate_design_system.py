#!/usr/bin/env python3
"""Validate the Stitch-inspired extract-design TOML and report coverage."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import Any, Iterable


REQUIRED_TABLES = (
    "metadata",
    "units",
    "fonts",
    "icons",
    "colors",
    "typography",
    "rounded",
    "spacing",
    "components",
    "breakpoints",
    "containers",
    "shadows",
    "motion",
    "layout",
    "variants",
    "implementation",
    "extensions",
)

TYPOGRAPHY_PROPERTIES = {
    "fontFamily",
    "fontSize",
    "fontWeight",
    "lineHeight",
    "letterSpacing",
    "fontFeature",
    "fontVariation",
}

COMPONENT_PROPERTIES = {
    "backgroundColor",
    "textColor",
    "typography",
    "rounded",
    "padding",
    "size",
    "height",
    "width",
}

COLOR = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
DIMENSION = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)(?:px|em|rem)$")
NUMBER = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")
REFERENCE = re.compile(r"^\{([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+)\}$")
PX_VALUE = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)px$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate design-system.toml structure, types, references, and coverage."
    )
    parser.add_argument("file", type=Path, help="Path to design-system.toml")
    return parser.parse_args()


def read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid TOML: {exc}") from None


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_filled(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(is_filled(item) for item in value.values())
    if isinstance(value, list):
        return bool(value)
    return value is not None


def is_reference(value: Any) -> bool:
    return isinstance(value, str) and REFERENCE.fullmatch(value.strip()) is not None


def is_dimension(value: Any, *, allow_zero: bool = True) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return bool(
        DIMENSION.fullmatch(text)
        or is_reference(text)
        or (allow_zero and text == "0")
    )


def iter_values(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_values(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_values(child, (*path, str(index)))
    else:
        yield path, value


def resolve_path(data: dict[str, Any], reference: str) -> Any:
    current: Any = data
    for part in reference.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(reference)
        current = current[part]
    return current


def warn_px(path: str, value: Any, warnings: list[str]) -> None:
    if not isinstance(value, str) or not PX_VALUE.fullmatch(value.strip()):
        return
    if value.strip() in {"0px", "1px"} or path == "rounded.full":
        return
    warnings.append(f"scalable dimension uses px; prefer rem with a px comment: {path}")


def validate_units(data: dict[str, Any], errors: list[str]) -> None:
    units = data.get("units")
    if not isinstance(units, dict):
        return

    root_size = units.get("rootFontSizePx")
    if not is_number(root_size) or root_size <= 0:
        errors.append("units.rootFontSizePx must be a number greater than zero")
    if units.get("scalableUnit") != "rem":
        errors.append('units.scalableUnit must be "rem"')
    if units.get("fixedUnit") != "px":
        errors.append('units.fixedUnit must be "px"')

    outputs = units.get("outputs")
    if (
        not isinstance(outputs, list)
        or not all(isinstance(item, str) for item in outputs)
        or not {"rem", "px"}.issubset(outputs)
    ):
        errors.append('units.outputs must include both "rem" and "px"')


def validate_colors(
    colors: dict[str, Any], errors: list[str], coverage: list[str]
) -> None:
    filled = 0
    for name, value in colors.items():
        path = f"colors.{name}"
        if not isinstance(value, str):
            errors.append(f"color must be a string: {path}")
            continue
        if not value.strip():
            continue
        filled += 1
        if not COLOR.fullmatch(value.strip()) and not is_reference(value):
            errors.append(f"color must be 6/8-digit sRGB hex or a reference: {path}")
    coverage.append(f"colors: {filled}/{len(colors)}")


def validate_typography(
    typography: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    coverage: list[str],
) -> None:
    filled_roles = 0
    for role, token in typography.items():
        role_path = f"typography.{role}"
        if not isinstance(token, dict):
            errors.append(f"typography token must be a table: {role_path}")
            continue
        if is_filled(token):
            filled_roles += 1

        for prop, value in token.items():
            path = f"{role_path}.{prop}"
            if prop not in TYPOGRAPHY_PROPERTIES:
                warnings.append(f"unknown typography property: {path}")
                continue
            if not is_filled(value):
                continue

            if prop in {"fontFamily", "fontFeature", "fontVariation"}:
                if not isinstance(value, str):
                    errors.append(f"typography property must be a string: {path}")
            elif prop in {"fontSize", "letterSpacing"}:
                if not is_dimension(value):
                    errors.append(f"typography property must be a dimension: {path}")
                elif prop == "fontSize":
                    warn_px(path, value, warnings)
            elif prop == "fontWeight":
                if not (
                    is_number(value)
                    or is_reference(value)
                    or (isinstance(value, str) and NUMBER.fullmatch(value.strip()))
                ):
                    errors.append(f"fontWeight must be numeric or a reference: {path}")
            elif prop == "lineHeight":
                if not (
                    is_number(value)
                    or is_dimension(value)
                    or (isinstance(value, str) and NUMBER.fullmatch(value.strip()))
                ):
                    errors.append(
                        f"lineHeight must be unitless, a dimension, or a reference: {path}"
                    )

    coverage.append(f"typography: {filled_roles}/{len(typography)} roles")


def validate_dimension_map(
    name: str,
    values: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    coverage: list[str],
    *,
    allow_number: bool = False,
) -> None:
    filled = 0
    for token, value in values.items():
        path = f"{name}.{token}"
        if not is_filled(value):
            continue
        filled += 1
        if allow_number and is_number(value):
            continue
        if not is_dimension(value):
            if allow_number and isinstance(value, str):
                warnings.append(
                    f"non-dimension spacing value retained as a string: {path}"
                )
                continue
            errors.append(f"token must be a dimension or reference: {path}")
            continue
        warn_px(path, value, warnings)
    coverage.append(f"{name}: {filled}/{len(values)}")


def validate_components(
    components: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    coverage: list[str],
) -> None:
    filled_components = 0
    dimension_properties = {"rounded", "padding", "size", "height", "width"}

    for component, token in components.items():
        component_path = f"components.{component}"
        if not isinstance(token, dict):
            errors.append(f"component token must be a table: {component_path}")
            continue
        if is_filled(token):
            filled_components += 1

        for prop, value in token.items():
            path = f"{component_path}.{prop}"
            if prop not in COMPONENT_PROPERTIES:
                warnings.append(f"unknown component property: {path}")
                continue
            if not is_filled(value):
                continue

            if prop in {"backgroundColor", "textColor"}:
                if not (
                    isinstance(value, str)
                    and (COLOR.fullmatch(value.strip()) or is_reference(value))
                ):
                    errors.append(f"component color must be hex or a reference: {path}")
            elif prop == "typography":
                if not is_reference(value):
                    errors.append(f"component typography must be a reference: {path}")
            elif prop in dimension_properties:
                if not is_dimension(value):
                    errors.append(f"component property must be a dimension: {path}")

    coverage.append(f"components: {filled_components}/{len(components)}")


def validate_references(
    data: dict[str, Any], errors: list[str]
) -> None:
    for source_path, value in iter_values(data):
        if not is_reference(value):
            continue
        match = REFERENCE.fullmatch(value.strip())
        assert match is not None
        target_path = match.group(1)
        source = ".".join(source_path)
        try:
            target = resolve_path(data, target_path)
        except KeyError:
            errors.append(f"dangling token reference at {source}: {value}")
            continue

        if isinstance(target, dict):
            composite_allowed = (
                bool(source_path)
                and source_path[0] == "components"
                and target_path.startswith("typography.")
            )
            if not composite_allowed:
                errors.append(f"reference must target a primitive at {source}: {value}")
        elif not is_filled(target):
            errors.append(f"reference targets an empty token at {source}: {value}")


def simple_coverage(name: str, values: dict[str, Any], coverage: list[str]) -> None:
    filled = sum(1 for value in values.values() if is_filled(value))
    coverage.append(f"{name}: {filled}/{len(values)}")


def validate(data: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    coverage: list[str] = []

    version = data.get("version")
    if version is not None and (not isinstance(version, str) or not version.strip()):
        errors.append("version must be a non-empty string when present")

    name = data.get("name")
    if not isinstance(name, str):
        errors.append("name must be a string")
    elif not name.strip():
        warnings.append("name is empty")

    if "description" in data and not isinstance(data["description"], str):
        errors.append("description must be a string")

    for table_name in REQUIRED_TABLES:
        value = data.get(table_name)
        if value is None:
            errors.append(f"missing table: [{table_name}]")
        elif not isinstance(value, dict):
            errors.append(f"value must be a table: [{table_name}]")

    validate_units(data, errors)

    colors = data.get("colors")
    if isinstance(colors, dict):
        validate_colors(colors, errors, coverage)

    typography = data.get("typography")
    if isinstance(typography, dict):
        validate_typography(typography, errors, warnings, coverage)

    for group, allow_number in (
        ("rounded", False),
        ("spacing", True),
        ("breakpoints", False),
        ("containers", False),
    ):
        values = data.get(group)
        if isinstance(values, dict):
            validate_dimension_map(
                group,
                values,
                errors,
                warnings,
                coverage,
                allow_number=allow_number,
            )

    components = data.get("components")
    if isinstance(components, dict):
        validate_components(components, errors, warnings, coverage)

    for group in ("fonts", "icons", "shadows", "motion"):
        values = data.get(group)
        if isinstance(values, dict):
            simple_coverage(group, values, coverage)

    implementation = data.get("implementation")
    if isinstance(implementation, dict):
        output_targets = implementation.get("outputTargets")
        if not isinstance(output_targets, list) or not all(
            isinstance(item, str) for item in output_targets
        ):
            errors.append("implementation.outputTargets must be an array of strings")

    validate_references(data, errors)

    for item in coverage:
        counts = re.search(r": (\d+)/(\d+)", item)
        if counts and counts.group(1) == "0":
            warnings.append(f"group is structurally valid but empty: {item.split(':', 1)[0]}")

    return errors, warnings, coverage


def main() -> int:
    args = parse_args()
    try:
        data = read_toml(args.file)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors, warnings, coverage = validate(data)

    print(f"File: {args.file.resolve()}")
    print("Coverage:")
    for item in coverage:
        print(f"  {item}")

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("Errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Result: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
