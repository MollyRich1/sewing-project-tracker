from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.helpers import (
    get_projects_blocking_pattern_delete,
    parse_non_negative_float,
    parse_quantity_to_cut,
    pattern_is_deletable,
    pattern_requires_lining,
)
from app.images import delete_local_image, replace_image
from app.models import Pattern, PatternPiece, db

bp = Blueprint("patterns", __name__, url_prefix="/patterns")


def _blank_pattern_form():
    return {
        "name": "",
        "notes": "",
        "estimated_hours": "",
        "outer_yards_required": "",
        "lining_yards_required": "",
        "notions": "",
    }


def _pattern_form_from_model(pattern):
    lining = pattern.lining_yards_required
    return {
        "name": pattern.name,
        "notes": pattern.notes or "",
        "estimated_hours": pattern.estimated_hours,
        "outer_yards_required": pattern.outer_yards_required,
        "lining_yards_required": "" if lining is None else lining,
        "notions": pattern.notions or "",
    }


def _pattern_form_from_request(form):
    return {
        "name": form.get("name", "").strip(),
        "notes": form.get("notes", "").strip(),
        "estimated_hours": form.get("estimated_hours", "").strip(),
        "outer_yards_required": form.get("outer_yards_required", "").strip(),
        "lining_yards_required": form.get("lining_yards_required", "").strip(),
        "notions": form.get("notions", "").strip(),
    }


def _apply_pattern_form(pattern, values):
    if not values["name"]:
        raise ValueError("Name is required.")
    pattern.name = values["name"]
    pattern.notes = values["notes"] or None
    pattern.estimated_hours = parse_non_negative_float(
        values["estimated_hours"], "Estimated hours"
    )
    pattern.outer_yards_required = parse_non_negative_float(
        values["outer_yards_required"], "Outer yards required"
    )
    pattern.lining_yards_required = parse_non_negative_float(
        values["lining_yards_required"],
        "Lining yards required",
        required=False,
    )
    pattern.notions = values["notions"] or None


def _blank_piece_form():
    return {
        "piece_name": "",
        "quantity_to_cut": "",
        "measurements": "",
        "fabric_type": "",
        "notes": "",
    }


def _piece_form_from_model(piece):
    return {
        "piece_name": piece.piece_name,
        "quantity_to_cut": piece.quantity_to_cut,
        "measurements": piece.measurements or "",
        "fabric_type": piece.fabric_type or "",
        "notes": piece.notes or "",
    }


def _piece_form_from_request(form):
    return {
        "piece_name": form.get("piece_name", "").strip(),
        "quantity_to_cut": form.get("quantity_to_cut", "").strip(),
        "measurements": form.get("measurements", "").strip(),
        "fabric_type": form.get("fabric_type", "").strip(),
        "notes": form.get("notes", "").strip(),
    }


def _apply_piece_form(piece, values):
    if not values["piece_name"]:
        raise ValueError("Piece name is required.")
    piece.piece_name = values["piece_name"]
    piece.quantity_to_cut = parse_quantity_to_cut(values["quantity_to_cut"])
    piece.measurements = values["measurements"] or None
    piece.fabric_type = values["fabric_type"] or None
    piece.notes = values["notes"] or None


@bp.route("/")
def list_patterns():
    patterns = Pattern.query.order_by(Pattern.name).all()
    return render_template("patterns/list.html", patterns=patterns)


@bp.route("/new", methods=["GET", "POST"])
def create_pattern():
    if request.method == "POST":
        values = _pattern_form_from_request(request.form)
        pattern = Pattern(
            name="placeholder",
            estimated_hours=0,
            outer_yards_required=0,
        )
        try:
            _apply_pattern_form(pattern, values)
            replace_image(pattern, request.files.get("image"), "patterns")
        except ValueError as error:
            return render_template(
                "patterns/form.html",
                title="Add pattern",
                form=values,
                error=str(error),
            ), 400
        db.session.add(pattern)
        db.session.commit()
        flash("Pattern saved.")
        return redirect(url_for("patterns.detail", pattern_id=pattern.id))

    return render_template(
        "patterns/form.html",
        title="Add pattern",
        form=_blank_pattern_form(),
        error=None,
    )


@bp.route("/<int:pattern_id>")
def detail(pattern_id):
    pattern = db.get_or_404(Pattern, pattern_id)
    return render_template(
        "patterns/detail.html",
        pattern=pattern,
        piece_form=_blank_piece_form(),
        piece_error=None,
        pattern_requires_lining=pattern_requires_lining(pattern),
        is_deletable=pattern_is_deletable(pattern),
    )


@bp.route("/<int:pattern_id>/edit", methods=["GET", "POST"])
def edit_pattern(pattern_id):
    pattern = db.get_or_404(Pattern, pattern_id)
    if request.method == "POST":
        values = _pattern_form_from_request(request.form)
        try:
            _apply_pattern_form(pattern, values)
            previous = replace_image(
                pattern, request.files.get("image"), "patterns"
            )
        except ValueError as error:
            return render_template(
                "patterns/form.html",
                title="Edit pattern",
                form=values,
                error=str(error),
                pattern=pattern,
            ), 400
        db.session.commit()
        delete_local_image(previous)
        flash("Pattern updated.")
        return redirect(url_for("patterns.detail", pattern_id=pattern.id))

    return render_template(
        "patterns/form.html",
        title="Edit pattern",
        form=_pattern_form_from_model(pattern),
        error=None,
        pattern=pattern,
    )


@bp.route("/<int:pattern_id>/delete", methods=["GET", "POST"])
def delete_pattern(pattern_id):
    pattern = db.get_or_404(Pattern, pattern_id)
    blocking = get_projects_blocking_pattern_delete(pattern)
    if blocking:
        return render_template(
            "patterns/delete.html",
            pattern=pattern,
            blocking_projects=blocking,
        ), 409 if request.method == "POST" else 200

    if request.method == "POST":
        image_paths = [pattern.image_url] + [
            piece.image_url for piece in pattern.pieces
        ]
        db.session.delete(pattern)
        db.session.commit()
        for image_path in image_paths:
            delete_local_image(image_path)
        flash("Pattern deleted.")
        return redirect(url_for("patterns.list_patterns"))

    return render_template(
        "patterns/delete.html",
        pattern=pattern,
        blocking_projects=[],
    )


@bp.route("/<int:pattern_id>/pieces", methods=["POST"])
def add_piece(pattern_id):
    pattern = db.get_or_404(Pattern, pattern_id)
    values = _piece_form_from_request(request.form)
    piece = PatternPiece(piece_name="placeholder", quantity_to_cut=1)
    try:
        _apply_piece_form(piece, values)
        replace_image(piece, request.files.get("image"), "pieces")
    except ValueError as error:
        return render_template(
            "patterns/detail.html",
            pattern=pattern,
            piece_form=values,
            piece_error=str(error),
            pattern_requires_lining=pattern_requires_lining(pattern),
            is_deletable=pattern_is_deletable(pattern),
        ), 400
    piece.pattern = pattern
    db.session.add(piece)
    db.session.commit()
    flash("Pattern piece added.")
    return redirect(url_for("patterns.detail", pattern_id=pattern.id))


@bp.route("/<int:pattern_id>/pieces/<int:piece_id>/edit", methods=["GET", "POST"])
def edit_piece(pattern_id, piece_id):
    pattern = db.get_or_404(Pattern, pattern_id)
    piece = db.session.get(PatternPiece, piece_id)
    if piece is None or piece.pattern_id != pattern.id:
        return ("Pattern piece not found.", 404)

    if request.method == "POST":
        values = _piece_form_from_request(request.form)
        try:
            _apply_piece_form(piece, values)
            previous = replace_image(
                piece, request.files.get("image"), "pieces"
            )
        except ValueError as error:
            return render_template(
                "patterns/piece_form.html",
                pattern=pattern,
                piece=piece,
                form=values,
                error=str(error),
            ), 400
        db.session.commit()
        delete_local_image(previous)
        flash("Pattern piece updated.")
        return redirect(url_for("patterns.detail", pattern_id=pattern.id))

    return render_template(
        "patterns/piece_form.html",
        pattern=pattern,
        piece=piece,
        form=_piece_form_from_model(piece),
        error=None,
    )


@bp.route("/<int:pattern_id>/pieces/<int:piece_id>/delete", methods=["GET", "POST"])
def delete_piece(pattern_id, piece_id):
    pattern = db.get_or_404(Pattern, pattern_id)
    piece = db.session.get(PatternPiece, piece_id)
    if piece is None or piece.pattern_id != pattern.id:
        return ("Pattern piece not found.", 404)

    if request.method == "POST":
        image_url = piece.image_url
        db.session.delete(piece)
        db.session.commit()
        delete_local_image(image_url)
        flash("Pattern piece deleted.")
        return redirect(url_for("patterns.detail", pattern_id=pattern.id))

    return render_template(
        "patterns/delete_piece.html",
        pattern=pattern,
        piece=piece,
    )
