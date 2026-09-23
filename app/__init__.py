import os
import sqlite3

from flask import Flask, abort, flash, redirect, request, send_from_directory, url_for
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite does not enforce foreign keys unless this pragma is on."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    os.makedirs(app.instance_path, exist_ok=True)

    default_db = "sqlite:///" + os.path.join(app.instance_path, "sewing.db")
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", default_db)
    app.config.setdefault(
        "UPLOAD_FOLDER", os.path.join(app.instance_path, "uploads")
    )

    if test_config:
        app.config.update(test_config)

    from app.images import (
        IMAGE_CATEGORIES,
        ensure_upload_directories,
        is_stored_upload,
        project_image_ref,
        public_image_url,
    )
    from app.models import db, ensure_schema
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.fabrics import bp as fabrics_bp
    from app.routes.patterns import bp as patterns_bp
    from app.routes.projects import bp as projects_bp

    db.init_app(app)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(fabrics_bp)
    app.register_blueprint(patterns_bp)
    app.register_blueprint(projects_bp)
    app.add_template_global(public_image_url, name="image_src")
    app.add_template_global(project_image_ref, name="project_image_ref")

    with app.app_context():
        ensure_schema()
        ensure_upload_directories()

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables and any new optional columns."""
        ensure_schema()
        ensure_upload_directories()
        print("Initialized the database.")

    @app.get("/uploads/<category>/<filename>")
    def uploaded_file(category, filename):
        if category not in IMAGE_CATEGORIES or not is_stored_upload(
            f"{category}/{filename}"
        ):
            abort(404)
        return send_from_directory(
            os.path.join(app.config["UPLOAD_FOLDER"], category),
            filename,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(error):
        flash("That image is too large. Please use a file under 5 MB.")
        target = request.referrer or url_for("dashboard.index")
        return redirect(target)

    from seed import register_seed_commands

    register_seed_commands(app)

    return app
