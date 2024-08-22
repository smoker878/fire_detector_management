import datetime

from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import send_file
from werkzeug.exceptions import abort
from docxtpl import DocxTemplate
import io

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

def timestamp_to_loccaltime(timesamp):
    return timesamp + datetime.timedelta(0, 28800)

def get_form(requistion_id):
    db = get_db()
    f = db.execute("SELECT * FROM BypassRequistion WHERE requistion_id = ?", (requistion_id,)).fetchone()
    Bypass_device = db.execute("SELECT device FROM Bypass_device WHERE requistion_id = ?", (requistion_id,)).fetchall()
    state = form_state(f)
    form_time = {}
    if f["excute_date"]:
        form_time["excute_date"] = f["excute_date"] + datetime.timedelta(0, 28800)
    if f["reset_date"]:
        form_time["reset_date"] = f["reset_date"] + datetime.timedelta(0, 28800)
    if f["apply_date"]:
        form_time["apply_date"] = f["apply_date"] + datetime.timedelta(0, 28800)

    return f, Bypass_device, state, form_time

@bp.route("/form/<requistion_id>")
@login_required
def form(requistion_id):
    f, Bypass_device, state, form_time = get_form(requistion_id)

    if f['reset_person_id']: #已復原
        db = get_db()
        need_reset = db.execute("SELECT B.device FROM Bypass_device B "
                                "WHERE requistion_id = ? AND NOT EXISTS"
                                "(SELECT device FROM CurrentBypass C WHERE B.device=C.device)",
                                (requistion_id,)).fetchall()
        return render_template("form/form.html", f=f, Bypass_device=Bypass_device, state=state, form_time = form_time, need_reset = need_reset)

    return render_template("form/form.html", f = f, Bypass_device = Bypass_device, state = state, form_time = form_time)

@bp.route("/form_docx/<requistion_id>")
def form_docx(requistion_id):
    f, Bypass_device, state, form_time = get_form(requistion_id)
    all_device = [divice[0] for divice in Bypass_device]
    all_device = ", ".join(all_device)
    f_keys = f.keys()
    context = {f_keys[i]:f[i] for i in range(len(f))}
    context['all_device'] = all_device
    context.update(form_time)
    doc = DocxTemplate('flaskr/templates/bypass_form_tpl.docx')
    doc.render(context)
    output = io.BytesIO()  # 保存到 BytesIO 物件
    doc.save(output)
    output.seek(0)  #移到文件開頭

    return send_file(output, as_attachment=True, download_name=f"{f['work_name']}_單號{f['work_id']}.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


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
            requistion_id = db.execute("SELECT requistion_id FROM BypassRequistion WHERE work_id = ? AND predict_to_work_date =?", (work_id, predict_to_work_date)).fetchone()
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
    this_form_applier = db.execute("SELECT applier_id FROM BypassRequistion WHERE requistion_id = ?", (requistion_id,)).fetchone()
    if this_form_applier[0] == g.user['user_id']:
        db.execute("DELETE FROM BypassRequistion WHERE  requistion_id = ?",(requistion_id,))
        db.commit()
    return redirect(url_for("form.history"))

@bp.route("/history",methods=("GET", "POST"))
@login_required
def history():
    db = get_db()
    base_query = "SELECT * FROM BypassRequistion"
    conditions = []
    parameters = []

    if request.args:
        if work_name := request.args.get('work_name'):
            conditions.append("work_name LIKE ?")
            parameters.append(f"%{work_name}%")
        if work_id := request.args.get('work_id'):
            conditions.append("CAST(work_id AS TEXT) LIKE ?")
            parameters.append(f"%{work_id}%")
        if requistion_id := request.args.get('requistion_id'):
            conditions.append("CAST(requistion_id AS TEXT) LIKE ?")
            parameters.append(f"%{requistion_id}%")
        if predict_to_work_date_start := request.args.get('predict_to_work_date_start'):
            conditions.append("predict_to_work_date >= ?")
            parameters.append(predict_to_work_date_start)
        if predict_to_work_date_end := request.args.get('predict_to_work_date_end'):
            conditions.append("predict_to_work_date <= ?")
            parameters.append(predict_to_work_date_end)
        if applier := request.args.get('applier'):
            conditions.append("applier LIKE ?")
            parameters.append(f"%{applier}%")

        if conditions:
            query = f"{base_query} WHERE {' AND '.join(conditions)} ORDER BY requistion_id DESC"
        else:
            query = f"{base_query} ORDER BY requistion_id DESC"
    else:
        query = f"{base_query} ORDER BY requistion_id DESC"

    all_form = db.execute(query, parameters).fetchall()
    return render_template("form/history.html", all_form=all_form)