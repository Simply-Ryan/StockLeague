from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database.db_manager import DatabaseManager
from helpers import apology

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log user in (migrated from main app)."""
    # Clear any existing session
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return apology("must provide username", 403)

        if not password:
            return apology("must provide password", 403)

        db = DatabaseManager()
        user = db.get_user_by_username(username)

        if not user or not check_password_hash(user.get("hash"), password):
            return apology("invalid username and/or password", 403)

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        flash("Logged in successfully!")
        return redirect("/")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Log user out (migrated from main app)."""
    session.clear()
    flash("Logged out successfully!")
    return redirect("/")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user (migrated from main app)."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)

        if not password:
            return apology("must provide password", 400)

        if not confirmation:
            return apology("must confirm password", 400)

        if password != confirmation:
            return apology("passwords must match", 400)

        db = DatabaseManager()
        if db.get_user_by_username(username):
            return apology("username already exists", 400)

        hash_val = generate_password_hash(password)
        user_id = db.create_user(username, hash_val)

        session["user_id"] = user_id
        session["username"] = username

        flash("Registered successfully!")
        return redirect("/")

    return render_template("register.html")
