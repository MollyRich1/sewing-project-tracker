from flask import Blueprint, render_template

from app.constants import (
    PROJECT_STATUSES,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PLANNED,
)
from app.models import Fabric, Pattern, Project

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    projects_by_status = {
        status: (
            Project.query.filter_by(status=status)
            .order_by(Project.created_at.desc())
            .all()
        )
        for status in PROJECT_STATUSES
    }
    return render_template(
        "dashboard.html",
        planned_projects=projects_by_status[STATUS_PLANNED],
        in_progress_projects=projects_by_status[STATUS_IN_PROGRESS],
        completed_projects=projects_by_status[STATUS_COMPLETED],
        statuses=PROJECT_STATUSES,
        has_patterns=Pattern.query.first() is not None,
        has_fabrics=Fabric.query.first() is not None,
    )
