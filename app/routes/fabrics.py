from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.helpers import (
    fabric_is_deletable,
    get_projects_blocking_fabric_delete,
    parse_non_negative_float,
)
from app.images import delete_local_image, replace_image
from app.models import Fabric, db

bp = Blueprint("fabrics", __name__, url_prefix="/fabrics")


def _blank_form():
    return {
        "name": "",
        "yards_available": "",
        "description": "",
        "notes": "",
    }


def _form_from_model(fabric):
    return {
        "name": fabric.name,
        "yards_available": fabric.yards_available,
        "description": fabric.description or "",
        "notes": fabric.notes or "",
    }


def _form_from_request(form):
    return {
        "name": form.get("name", "").strip(),
        "yards_available": form.get("yards_available", "").strip(),
        "description": form.get("description", "").strip(),
        "notes": form.get("notes", "").strip(),
    }


def _apply_form(fabric, values):
    if not values["name"]:
        raise ValueError("Name is required.")
    fabric.name = values["name"]
    fabric.yards_available = parse_non_negative_float(
        values["yards_available"], "Yards available"
    )
    fabric.description = values["description"] or None
    fabric.notes = values["notes"] or None


@bp.route("/")
def list_fabrics():
    fabrics = Fabric.query.order_by(Fabric.name).all()
    return render_template("fabrics/list.html", fabrics=fabrics)


@bp.route("/new", methods=["GET", "POST"])
def create_fabric():
    if request.method == "POST":
        values = _form_from_request(request.form)
        fabric = Fabric(name="placeholder", yards_available=0)
        try:
            _apply_form(fabric, values)
            replace_image(fabric, request.files.get("image"), "fabrics")
        except ValueError as error:
            return render_template(
                "fabrics/form.html",
                title="Add fabric",
                form=values,
                error=str(error),
            ), 400
        db.session.add(fabric)
        db.session.commit()
        flash("Fabric saved.")
        return redirect(url_for("fabrics.list_fabrics"))

    return render_template(
        "fabrics/form.html", title="Add fabric", form=_blank_form(), error=None
    )


@bp.route("/<int:fabric_id>/edit", methods=["GET", "POST"])
def edit_fabric(fabric_id):
    fabric = db.get_or_404(Fabric, fabric_id)
    if request.method == "POST":
        values = _form_from_request(request.form)
        try:
            _apply_form(fabric, values)
            previous = replace_image(
                fabric, request.files.get("image"), "fabrics"
            )
        except ValueError as error:
            return render_template(
                "fabrics/form.html",
                title="Edit fabric",
                form=values,
                error=str(error),
                fabric=fabric,
            ), 400
        db.session.commit()
        delete_local_image(previous)
        flash("Fabric updated.")
        return redirect(url_for("fabrics.list_fabrics"))

    return render_template(
        "fabrics/form.html",
        title="Edit fabric",
        form=_form_from_model(fabric),
        error=None,
        fabric=fabric,
    )


@bp.route("/<int:fabric_id>/delete", methods=["GET", "POST"])
def delete_fabric(fabric_id):
    fabric = db.get_or_404(Fabric, fabric_id)
    blocking_projects = get_projects_blocking_fabric_delete(fabric)
    usages = []
    for project in blocking_projects:
        roles = []
        if project.outer_fabric_id == fabric.id:
            roles.append("Outer")
        if project.lining_fabric_id == fabric.id:
            roles.append("Lining")
        usages.append((project, " and ".join(roles)))

    if not fabric_is_deletable(fabric):
        return render_template(
            "fabrics/delete.html", fabric=fabric, usages=usages
        ), 409 if request.method == "POST" else 200

    if request.method == "POST":
        image_url = fabric.image_url
        db.session.delete(fabric)
        db.session.commit()
        delete_local_image(image_url)
        flash("Fabric deleted.")
        return redirect(url_for("fabrics.list_fabrics"))

    return render_template("fabrics/delete.html", fabric=fabric, usages=[])
