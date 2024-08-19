from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from .auth import login_required
from .db import get_db

bp = Blueprint("form", __name__, url_prefix="/form")


@bp.route('/')
def index():
    db = get_db()
    curry_bypass = db.execute("SELECT * FROM CurrentBypass").fetchall()
    return render_template("form/index.html", curry_bypass=curry_bypass)
@bp.route("/form/<requistion_id>")
@login_required
def form(requistion_id):
    db = get_db()
    BypassRequistion = db.execute("SELECT * FROM BypassRequistion WHERE requistion_id = ?", (requistion_id)).fetchone()
    Bypass_device = db.execute("SELECT * FROM Bypass_device WHERE requistion_id = ?", (requistion_id)).fetchall()
    return render_template("form/index.html", BypassRequistion = BypassRequistion, Bypass_device = Bypass_device)

@bp.route("/apply", methods=("GET", "POST"))
@login_required
def apply():
    if request.method == "POST":
        requistion_id = request.form["requistion_id"]
        apply_department = request.form["apply_department"]
        applier_id = request.form["applier_id"]
        applier = request.form["applier"]
        predict_to_work_date = request.form["predict_to_work_date"]
        work_id = request.form["work_id"]
        work_name = request.form["work_name"]
        contractor = request.form["contractor"]
        other_message = request.form["other_message"]
        device = request.form["device"]

        all_deviice = [(requistion_id, i.replace("\n", "").replace(" ", "").upper()) for i in device.split(",")]

        error = None

        # if not title:
        #     error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO BypassRequistion"
                "(requistion_id, apply_department, applier_id, applier, predict_to_work_date, work_id, work_name, contractor, other_message )"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (requistion_id, apply_department, applier_id, applier, predict_to_work_date, work_id, work_name, contractor, other_message),
            )
            db.executemany("INSERT INTO Bypass_device (requistion_id, device) VALUES (?, ?)",all_deviice)
            db.commit()
        return redirect(url_for("form.index"))
    return render_template("form/apply.html")

@bp.route("/excute/<requistion_id>")
@login_required
def excute(requistion_id):
    db = get_db()
    db.execute(
        "UPDATE BypassRequistion SET excute_date = CURRENT_TIMESTAMP, excute_department = ?, excutor_id = ?, excutor = ?"
        "WHERE  BypassRequistion = ?",
        (g.user['department'], g.user['user_id'], g.user['username'], requistion_id)
        )
    db.commit()
    return redirect(url_for("form.index"))

@bp.route("/reset/<requistion_id>")
@login_required
def reset(requistion_id):
    db = get_db()
    db.execute(
        "UPDATE BypassRequistion SET reset_date = CURRENT_TIMESTAMP, reset_department = ?, reset_person_id = ?, reset_person = ?"
        "WHERE  BypassRequistion = ?",
        (g.user['department'], g.user['user_id'], g.user['username'], requistion_id)
        )
    db.commit()
    return redirect(url_for("form.index"))

@bp.route("/delete/<requistion_id>")
@login_required
def delete(requistion_id):
    db = get_db()
    this_form_applier = db.execute("SELECT applier_id FROM BypassRequistion WHERE requistion_id = ?", requistion_id).fetchone()
    if this_form_applier == g.user['user_id']:
        db.execute(
            "UPDATE BypassRequistion SET excute_date = CURRENT_TIMESTAMP, excute_department = ?, excutor_id = ?, excutor = ?"
            " WHERE  BypassRequistion = ?",
            (g.user['department'], g.user['user_id'], g.user['username'], requistion_id)
            )
        db.commit()
    return redirect(url_for("form.index"))