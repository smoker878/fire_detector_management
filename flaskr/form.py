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

bp = Blueprint("form", __name__)


@bp.route('/')
def index():
    db = get_db()
    curry_bypass = db.execute("SELECT * FROM CurrentBypass").fetchall()
    curry_work = db.execute(
        "SELECT requistion_id, work_name FROM BypassRequistion WHERE excutor_id is not NULL AND reset_person_id is NULL"
    ).fetchall()
    return render_template("form/index.html", curry_bypass=curry_bypass, curry_work = curry_work)

def form_state(f):
    if f['reset_person_id']:
        return "🟢已復原"
    elif f['excutor_id']:
        return "⚠️Bypass執行中⚠️"
    else:
        return "📋申請中"

@bp.route("/form/<requistion_id>")
@login_required
def form(requistion_id):
    db = get_db()
    f = db.execute("SELECT * FROM BypassRequistion WHERE requistion_id = ?", (requistion_id)).fetchone()
    Bypass_device = db.execute("SELECT * FROM Bypass_device WHERE requistion_id = ?", (requistion_id)).fetchall()
    state = form_state(f)

    if f['reset_person_id']: #已復原
        need_reset = db.execute("SELECT B.device FROM Bypass_device B "
                                "WHERE requistion_id = ? AND NOT EXISTS"
                                "(SELECT device FROM CurrentBypass C WHERE B.device=C.device)",
                                (requistion_id)).fetchall()
        return render_template("form/form.html", f=f, Bypass_device=Bypass_device, state=state, need_reset = need_reset)

    return render_template("form/form.html", f = f, Bypass_device = Bypass_device, state = state)

@bp.route("/apply", methods=("GET", "POST"))
@login_required
def apply():
    if request.method == "POST":

        apply_department = request.form["apply_department"]
        applier_id = request.form["applier_id"]
        applier = request.form["applier"]
        predict_to_work_date = request.form["predict_to_work_date"]
        work_id = request.form["work_id"]
        work_name = request.form["work_name"]
        contractor = request.form["contractor"]
        other_message = request.form["other_message"]
        device = request.form["device"]



        error = None

        # if not title:
        #     error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO BypassRequistion"
                "(apply_department, applier_id, applier, predict_to_work_date, work_id, work_name, contractor, other_message )"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (apply_department, applier_id, applier, predict_to_work_date, work_id, work_name, contractor, other_message),
            )
            db.commit()
            requistion_id = db.execute("SELECT requistion_id FROM BypassRequistion WHERE work_id = ?", (work_id,)).fetchone()
            all_device = [(requistion_id[0], i.replace("\n", "").replace(" ", "").upper()) for i in device.split(",")]
            db.executemany("INSERT INTO Bypass_device (requistion_id, device) VALUES (?, ?)", all_device)
            db.commit()
        return redirect(url_for("form.index"))
    return render_template("form/apply.html")

@bp.route("/excute/<requistion_id>")
@login_required
def excute(requistion_id):
    db = get_db()
    db.execute(
        "UPDATE BypassRequistion SET excute_date = CURRENT_TIMESTAMP, excute_department = ?, excutor_id = ?, excutor = ?"
        "WHERE  requistion_id = ?",
        (g.user['department'], g.user['user_id'], g.user['username'], requistion_id)
        )
    db.commit()
    return redirect(url_for("form.history"))

@bp.route("/reset/<requistion_id>")
@login_required
def reset(requistion_id):
    db = get_db()
    db.execute(
        "UPDATE BypassRequistion SET reset_date = CURRENT_TIMESTAMP, reset_department = ?, reset_person_id = ?, reset_person = ?"
        "WHERE  requistion_id = ?",
        (g.user['department'], g.user['user_id'], g.user['username'], requistion_id)
        )
    db.commit()
    return redirect(url_for("form.history"))

@bp.route("/delete/<requistion_id>")
@login_required
def delete(requistion_id):
    db = get_db()
    this_form_applier = db.execute("SELECT applier_id FROM BypassRequistion WHERE requistion_id = ?", requistion_id).fetchone()
    if this_form_applier == g.user['user_id']:
        db.execute("DELETE FROM BypassRequistion WHERE  requistion_id = ?",(requistion_id,))
        db.commit()
    return redirect(url_for("form.history"))

@bp.route("/history")
@login_required
def history():
    db = get_db()
    all_form = db.execute("SELECT * FROM BypassRequistion").fetchall()
    return render_template("form/history.html", all_form = all_form)