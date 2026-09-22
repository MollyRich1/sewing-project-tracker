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
