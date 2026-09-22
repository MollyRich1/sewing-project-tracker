def get_projects_blocking_pattern_delete(pattern):
    """Return projects that currently use this pattern."""
    return list(pattern.projects)


def pattern_is_deletable(pattern):
    return len(pattern.projects) == 0


def get_projects_blocking_fabric_delete(fabric):
    """Return unique projects that use this fabric as outer or lining."""
    projects_by_id = {}
    for project in fabric.outer_projects:
        projects_by_id[project.id] = project
    for project in fabric.lining_projects:
        projects_by_id[project.id] = project
    return list(projects_by_id.values())


def fabric_is_deletable(fabric):
    return len(get_projects_blocking_fabric_delete(fabric)) == 0


def pattern_requires_lining(pattern):
    """Lining is required only when lining_yards_required is a number.

    None means the pattern does not use lining. 0 means it does, but
    needs zero yards.
    """
    return pattern.lining_yards_required is not None


def parse_non_negative_float(raw, field_label, required=True):
    text = "" if raw is None else str(raw).strip()
    if text == "":
        if required:
            raise ValueError(f"{field_label} is required.")
        return None
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"{field_label} must be a number.")
    if number < 0:
        raise ValueError(f"{field_label} cannot be negative.")
    return number


def parse_quantity_to_cut(raw):
    text = "" if raw is None else str(raw).strip()
    if text == "":
        raise ValueError("Quantity to cut is required.")
    try:
        number = int(text)
    except ValueError:
        raise ValueError("Quantity to cut must be a whole number.")
    if number < 1:
        raise ValueError("Quantity to cut must be at least 1.")
    return number


def has_enough_fabric(yards_available, yards_required):
    """Compare stash amount to a pattern requirement.

    Returns True/False, or None if a comparison cannot be made yet.
    """
    if yards_available is None or yards_required is None:
        return None
    return yards_available >= yards_required
