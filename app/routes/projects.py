from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.constants import PROJECT_STATUSES, STATUS_IN_PROGRESS
from app.helpers import has_enough_fabric, pattern_requires_lining
from app.images import delete_local_image, replace_image
from app.models import Fabric, Pattern, Project, db

bp = Blueprint("projects", __name__, url_prefix="/projects")


def _parse_id(raw, label, required=True):
    text = "" if raw is None else str(raw).strip()
    if not text:
        if required:
            raise ValueError(f"{label} is required.")
        return None
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"{label} is invalid.")


def _form_from_request(values):
    return {
        "name": values.get("name", "").strip(),
        "pattern_id": values.get("pattern_id", "").strip(),
        "outer_fabric_id": values.get("outer_fabric_id", "").strip(),
        "lining_fabric_id": values.get("lining_fabric_id", "").strip(),
        "status": values.get("status", STATUS_IN_PROGRESS).strip(),
        "notes": values.get("notes", "").strip(),
    }


def _blank_form():
    return {
        "name": "",
        "pattern_id": "",
        "outer_fabric_id": "",
        "lining_fabric_id": "",
        "status": STATUS_IN_PROGRESS,
        "notes": "",
    }


def _form_from_model(project):
    return {
        "name": project.name,
        "pattern_id": str(project.pattern_id),
        "outer_fabric_id": str(project.outer_fabric_id),
        "lining_fabric_id": (
            "" if project.lining_fabric_id is None else str(project.lining_fabric_id)
        ),
        "status": project.status,
        "notes": project.notes or "",
    }


def _load_form_choices(form):
    patterns = Pattern.query.order_by(Pattern.name).all()
    fabrics = Fabric.query.order_by(Fabric.name).all()
    pattern_id = _safe_int(form["pattern_id"])
    outer_id = _safe_int(form["outer_fabric_id"])
    lining_id = _safe_int(form["lining_fabric_id"])
    pattern = db.session.get(Pattern, pattern_id) if pattern_id is not None else None
    outer_fabric = db.session.get(Fabric, outer_id) if outer_id is not None else None
    lining_fabric = db.session.get(Fabric, lining_id) if lining_id is not None else None
    return patterns, fabrics, pattern, outer_fabric, lining_fabric


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _apply_form(project, form):
    if not form["name"]:
        raise ValueError("Project name is required.")
    if form["status"] not in PROJECT_STATUSES:
        raise ValueError("Choose a valid project status.")

    pattern_id = _parse_id(form["pattern_id"], "Pattern")
    outer_fabric_id = _parse_id(form["outer_fabric_id"], "Outer fabric")
    lining_fabric_id = _parse_id(
        form["lining_fabric_id"], "Lining fabric", required=False
    )

    pattern = db.session.get(Pattern, pattern_id)
    outer_fabric = db.session.get(Fabric, outer_fabric_id)
    lining_fabric = (
        db.session.get(Fabric, lining_fabric_id)
        if lining_fabric_id is not None
        else None
    )
    if pattern is None:
        raise ValueError("Choose an existing pattern.")
    if outer_fabric is None:
        raise ValueError("Choose an existing outer fabric.")
    if lining_fabric_id is not None and lining_fabric is None:
        raise ValueError("Choose an existing lining fabric.")

    project.name = form["name"]
    project.pattern = pattern
    project.outer_fabric = outer_fabric
    project.lining_fabric = lining_fabric
    project.status = form["status"]
    project.notes = form["notes"] or None


def _render_form(title, form, error=None, project=None, status_code=200):
    patterns, fabrics, pattern, outer, lining = _load_form_choices(form)
    return render_template(
        "projects/form.html",
        title=title,
        form=form,
        error=error,
        project=project,
        patterns=patterns,
        fabrics=fabrics,
        statuses=PROJECT_STATUSES,
        selected_pattern=pattern,
        selected_outer=outer,
        selected_lining=lining,
        pattern_requires_lining=(
            pattern_requires_lining(pattern) if pattern is not None else False
        ),
        outer_enough=(
            has_enough_fabric(outer.yards_available, pattern.outer_yards_required)
            if outer is not None and pattern is not None
            else None
        ),
        lining_enough=(
            has_enough_fabric(
                lining.yards_available, pattern.lining_yards_required
            )
            if lining is not None
            and pattern is not None
            and pattern_requires_lining(pattern)
            else None
        ),
    ), status_code


@bp.route("/")
def list_projects():
    selected_status = request.args.get("status", STATUS_IN_PROGRESS)
    if selected_status not in PROJECT_STATUSES:
        selected_status = STATUS_IN_PROGRESS
    projects = (
        Project.query.filter_by(status=selected_status)
        .order_by(Project.created_at.desc())
        .all()
    )
    counts = {
        status: Project.query.filter_by(status=status).count()
        for status in PROJECT_STATUSES
    }
    return render_template(
        "projects/list.html",
        projects=projects,
        selected_status=selected_status,
        statuses=PROJECT_STATUSES,
        counts=counts,
    )


@bp.route("/new", methods=["GET", "POST"])
def create_project():
    if request.method == "POST":
        form = _form_from_request(request.form)
        project = Project(
            name="placeholder",
            pattern_id=0,
            outer_fabric_id=0,
            status=STATUS_IN_PROGRESS,
        )
        try:
            _apply_form(project, form)
            replace_image(project, request.files.get("image"), "projects")
        except ValueError as error:
            return _render_form(
                "Create project", form, error=str(error), status_code=400
            )
        db.session.add(project)
        db.session.commit()
        flash("Project saved.")
        return redirect(url_for("projects.detail", project_id=project.id))

    form = _form_from_request(request.args) if request.args else _blank_form()
    return _render_form("Create project", form)


@bp.route("/<int:project_id>")
def detail(project_id):
    project = db.get_or_404(Project, project_id)
    return render_template(
        "projects/detail.html",
        project=project,
        statuses=PROJECT_STATUSES,
        pattern_requires_lining=pattern_requires_lining(project.pattern),
        outer_enough=has_enough_fabric(
            project.outer_fabric.yards_available,
            project.pattern.outer_yards_required,
        ),
        lining_enough=(
            has_enough_fabric(
                project.lining_fabric.yards_available,
                project.pattern.lining_yards_required,
            )
            if project.lining_fabric is not None
            and pattern_requires_lining(project.pattern)
            else None
        ),
    )


@bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
def edit_project(project_id):
    project = db.get_or_404(Project, project_id)
    if request.method == "POST":
        form = _form_from_request(request.form)
        try:
            _apply_form(project, form)
            previous = replace_image(
                project, request.files.get("image"), "projects"
            )
        except ValueError as error:
            return _render_form(
                "Edit project",
                form,
                error=str(error),
                project=project,
                status_code=400,
            )
        db.session.commit()
        delete_local_image(previous)
        flash("Project updated.")
        return redirect(url_for("projects.detail", project_id=project.id))

    if request.args:
        form = _form_from_request(request.args)
    else:
        form = _form_from_model(project)
    return _render_form("Edit project", form, project=project)


@bp.route("/<int:project_id>/status", methods=["POST"])
def change_status(project_id):
    project = db.get_or_404(Project, project_id)
    status = request.form.get("status", "")
    if status not in PROJECT_STATUSES:
        return ("Choose a valid project status.", 400)
    project.status = status
    db.session.commit()
    flash("Project status updated.")
    return redirect(url_for("projects.list_projects", status=status))


@bp.route("/<int:project_id>/delete", methods=["GET", "POST"])
def delete_project(project_id):
    project = db.get_or_404(Project, project_id)
    if request.method == "POST":
        image_url = project.image_url
        db.session.delete(project)
        db.session.commit()
        delete_local_image(image_url)
        flash("Project deleted.")
        return redirect(url_for("projects.list_projects"))
    return render_template("projects/delete.html", project=project)
