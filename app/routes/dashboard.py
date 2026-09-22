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
    recent_patterns = Pattern.query.order_by(Pattern.created_at.desc()).limit(3).all()
    fabrics = Fabric.query.order_by(Fabric.created_at.desc()).all()
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(3).all()

    return render_template(
        "dashboard.html",
        planned_projects=projects_by_status[STATUS_PLANNED],
        in_progress_projects=projects_by_status[STATUS_IN_PROGRESS],
        completed_projects=projects_by_status[STATUS_COMPLETED],
        continue_project=(
            projects_by_status[STATUS_IN_PROGRESS][0]
            if projects_by_status[STATUS_IN_PROGRESS]
            else None
        ),
        project_counts={
            status: len(projects_by_status[status]) for status in PROJECT_STATUSES
        },
        recent_projects=recent_projects,
        recent_patterns=recent_patterns,
        recent_fabrics=fabrics[:4],
        fabric_count=len(fabrics),
        total_fabric_yards=sum(fabric.yards_available for fabric in fabrics),
        statuses=PROJECT_STATUSES,
        has_patterns=bool(recent_patterns),
        has_fabrics=bool(fabrics),
    )
