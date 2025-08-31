from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from auth import verify_user, verify_2fa_token
from db import query_db, execute_db
from utils import send_email
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib.units import inch
from datetime import datetime, timedelta
from reportlab.lib import colors
import io, random, decimal

bp = Blueprint('routes', __name__)

@bp.route('/')
def home():
    return redirect(url_for('routes.login_patient'))

@bp.route('/login/patient', methods=['GET', 'POST'])
def login_patient():
    if request.method == 'POST':
        user = verify_user(request.form['username'], request.form['password'])
        if user and user['role'] == 'patient':
            session['temp_user'] = user
            if not user['two_factor_secret']:
                flash('2FA not set up. Please contact admin.', 'warning')
                return redirect(url_for('routes.login_patient'))
            return redirect(url_for('routes.otp_verify'))
        flash('Invalid credentials or not a patient.')
    return render_template('login_patient.html')

@bp.route('/login/doctor', methods=['GET', 'POST'])
def login_doctor():
    if request.method == 'POST':
        user = verify_user(request.form['username'], request.form['password'])
        if user and user['role'] == 'doctor':
            session['user'] = user
            return redirect(url_for('routes.doctor_dashboard'))
        flash('Invalid credentials or not a doctor.')
    return render_template('login_doctor.html')

@bp.route('/otp-verify', methods=['GET', 'POST'])
def otp_verify():
    if request.method == 'POST':
        user = session.get('temp_user')
        if user and verify_2fa_token(user['two_factor_secret'], request.form['otp']):
            session['user'] = user
            session.pop('temp_user', None)
            return redirect(url_for('routes.patient_dashboard'))
        flash('Invalid OTP token.')
    return render_template('otp_verify.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('routes.home'))

@bp.route('/dashboard/patient')
def patient_dashboard():
    if 'user' not in session or session['user']['role'] != 'patient':
        return redirect(url_for('routes.login_patient'))

    patient_id = session['user']['id']
    details = query_db("SELECT age, gender, height_m, weight_kg FROM health_metrics WHERE patient_id = %s LIMIT 1", (patient_id,), one=True)
    return render_template('dashboard_patient.html', user=session['user'], patient_id=patient_id, patient_details=details)

@bp.route('/dashboard/doctor')
def doctor_dashboard():
    if 'user' not in session or session['user']['role'] != 'doctor':
        return redirect(url_for('routes.login_doctor'))
    doctor_id = session['user']['id']
    patients = query_db("SELECT DISTINCT patient_id FROM health_metrics WHERE doctor_id = %s", (doctor_id,))
    return render_template('dashboard_doctor.html', patients=patients)

@bp.route('/doctor/patient/<int:patient_id>')
def doctor_patient_detail(patient_id):
    if 'user' not in session or session['user']['role'] != 'doctor':
        return redirect(url_for('routes.login_doctor'))
    patient = query_db("SELECT * FROM health_metrics WHERE patient_id = %s ORDER BY timestamp DESC LIMIT 1", (patient_id,), one=True)
    return render_template('doctor_patient_detail.html', patient=patient)

@bp.route('/schedule', methods=['GET', 'POST'])
def schedule_meeting():
    if 'user' not in session:
        return redirect(url_for('routes.home'))

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        patient_id = request.form['patient_id']
        meeting_time = request.form['meeting_time']
        meeting_link = request.form['meeting_link']
        notes = request.form['notes']

        success = execute_db("""
            INSERT INTO meetings (doctor_id, patient_id, meeting_time, meeting_link, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (doctor_id, patient_id, meeting_time, meeting_link, notes))

        if success:
            send_email("recipient@example.com", "New Meeting Scheduled", f"Meeting on {meeting_time} at {meeting_link}")
            flash("Meeting scheduled successfully.")
        else:
            flash("Failed to schedule meeting.")

    return render_template('schedule_meeting.html')

@bp.route('/my-meetings')
def my_meetings():
    if 'user' not in session:
        return redirect(url_for('routes.home'))
    user = session['user']
    role_column = 'doctor_id' if user['role'] == 'doctor' else 'patient_id'
    meetings = query_db(f"SELECT * FROM meetings WHERE {role_column} = %s", (user['id'],))
    return render_template('meetings.html', meetings=meetings)

@bp.route('/api/patient_data')
def api_patient_data():
    if 'user' not in session or session['user']['role'] != 'patient':
        return jsonify({'error': 'Unauthorized'}), 403
    heart_rate = random.randint(65, 100)
    return jsonify({
        "heart_rate": heart_rate,
        "timestamp": datetime.now().isoformat(),
        "oxygen_saturation": random.randint(90, 100),
        "body_temperature": round(random.uniform(36.5, 37.5), 1),
        "respiratory_rate": random.randint(12, 20),
        "blood_pressure_systolic": random.randint(110, 130),
        "blood_pressure_diastolic": random.randint(70, 90),
        "derived_map": round(random.uniform(75, 95), 1)
    })

@bp.route('/api/patient_trends')
def patient_trends():
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    patient_id = request.args.get('patient_id', user['id'])
    since = datetime.now() - timedelta(hours=24)
    rows = query_db("""
        SELECT timestamp, heart_rate, oxygen_saturation, body_temperature, derived_map, respiratory_rate
        FROM health_metrics
        WHERE patient_id = %s AND timestamp >= %s
        ORDER BY timestamp ASC
    """, (patient_id, since))

    trends = {'heart_rate': [], 'oxygen_saturation': [], 'body_temperature': [], 'derived_map': [], 'respiratory_rate': []}
    for row in rows:
        ts = row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])
        for key in trends:
            if row[key] is not None:
                trends[key].append({'x': ts, 'y': row[key]})

    return jsonify(trends)

@bp.route('/generate-report')
def generate_report():
    if 'user' not in session:
        return redirect(url_for('routes.login_patient'))

    user = session['user']
    patient_id = user['id']

    metrics = query_db("""
        SELECT timestamp, heart_rate, respiratory_rate, body_temperature, oxygen_saturation,
               systolic_blood_pressure, diastolic_blood_pressure, derived_hrv, derived_pulse_pressure,
               derived_bmi, derived_map, risk_category
        FROM health_metrics
        WHERE patient_id = %s
        ORDER BY timestamp ASC LIMIT 100
    """, (patient_id,))

    all_patients = query_db("""
        SELECT derived_bmi, derived_map FROM health_metrics
        WHERE patient_id != %s AND derived_bmi IS NOT NULL AND derived_map IS NOT NULL
        LIMIT 100
    """, (patient_id,))

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40

    p.setFont("Helvetica-Bold", 18)
    p.drawString(72, y, f"Health Report Summary for: {user['username']}")
    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(72, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 20
    p.drawString(72, y, f"Total Health Records Analyzed: {len(metrics)}")
    y -= 40

    def create_line_chart(title, data, stroke_color=colors.darkblue):
        chart_data = [(i, float(v)) for i, v in enumerate(data) if v is not None]
        if not chart_data:
            return None
        d = Drawing(480, 250)
        lp = LinePlot()
        lp.x = 50
        lp.y = 50
        lp.height = 160
        lp.width = 360
        lp.data = [chart_data]
        lp.lines[0].strokeColor = stroke_color
        lp.lines[0].symbol = makeMarker("Circle")
        lp.xValueAxis.valueMin = 0
        lp.xValueAxis.valueMax = len(chart_data) - 1
        min_y = min(v for _, v in chart_data)
        max_y = max(v for _, v in chart_data)
        padding = (max_y - min_y) * 0.1 if max_y > min_y else 5
        lp.yValueAxis.valueMin = min_y - padding
        lp.yValueAxis.valueMax = max_y + padding
        lp.xValueAxis.labelTextFormat = '%d'
        lp.yValueAxis.labelTextFormat = '%.1f'
        d.add(lp)
        return d

    charts = [
        ("Heart Rate Trend", [m['heart_rate'] for m in metrics], colors.red),
        ("Respiratory Rate Trend", [m['respiratory_rate'] for m in metrics], colors.blue),
        ("Body Temperature Trend", [m['body_temperature'] for m in metrics], colors.orange),
        ("SpO2 Trend", [m['oxygen_saturation'] for m in metrics], colors.green),
        ("Pulse Pressure Trend", [m['derived_pulse_pressure'] for m in metrics], colors.purple),
        ("HRV Trend", [m['derived_hrv'] for m in metrics], colors.darkcyan)
    ]

    for i, (title, values, color) in enumerate(charts):
        if i > 0 and i % 3 == 0:
            p.showPage()
            y = height - 40
        chart = create_line_chart(title, values, color)
        if chart:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(72, y, title)
            chart.drawOn(p, 72, y - 220)
            y -= 240

    if all_patients:
        def to_float(val):
            return float(val) if isinstance(val, decimal.Decimal) else val

        patient_points = [(to_float(m['derived_bmi']), to_float(m['derived_map'])) for m in metrics if m['derived_bmi'] and m['derived_map']]
        other_points = [(to_float(m['derived_bmi']), to_float(m['derived_map'])) for m in all_patients]

        all_points = other_points + patient_points
        min_x = min(x for x, _ in all_points) - 1
        max_x = max(x for x, _ in all_points) + 1
        min_y = min(y for _, y in all_points) - 1
        max_y = max(y for _, y in all_points) + 1

        d = Drawing(480, 250)
        for x, y_val in other_points:
            px = 50 + (x - min_x) / (max_x - min_x) * 360
            py = 50 + (y_val - min_y) / (max_y - min_y) * 160
            d.add(Circle(px, py, 2, strokeColor=colors.grey, fillColor=colors.grey))

        for x, y_val in patient_points:
            px = 50 + (x - min_x) / (max_x - min_x) * 360
            py = 50 + (y_val - min_y) / (max_y - min_y) * 160
            d.add(Circle(px, py, 3, strokeColor=colors.red, fillColor=colors.red))

        d.add(String(60, 10, "BMI vs MAP Comparison (Red = This Patient)", fontSize=10))
        p.showPage()
        y = height - 40
        p.setFont("Helvetica-Bold", 12)
        p.drawString(72, y, "BMI vs MAP Comparison")
        d.drawOn(p, 72, y - 220)
        y -= 240

    latest = metrics[-1] if metrics else {}
    if latest:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(72, y, "Latest Health Snapshot:")
        p.setFont("Helvetica", 11)
        y -= 20
        for label, key in [
            ("Heart Rate", 'heart_rate'),
            ("Respiratory Rate", 'respiratory_rate'),
            ("Temperature", 'body_temperature'),
            ("SpO2", 'oxygen_saturation'),
            ("Systolic BP", 'systolic_blood_pressure'),
            ("Diastolic BP", 'diastolic_blood_pressure'),
            ("Pulse Pressure", 'derived_pulse_pressure'),
            ("HRV", 'derived_hrv'),
            ("MAP", 'derived_map'),
            ("BMI", 'derived_bmi'),
            ("Risk Category", 'risk_category')
        ]:
            if latest.get(key) is not None:
                p.drawString(80, y, f"{label}: {latest[key]}")
                y -= 15

        risk = latest.get('risk_category', '').lower()
        risk_msg = {
            'low': "The patient is in a stable condition.",
            'moderate': "Monitor closely for changes.",
            'high': "Immediate medical attention may be required."
        }.get(risk, "Risk level not available.")

        p.setFont("Helvetica-Bold", 12)
        p.drawString(72, y - 10, "Risk Interpretation:")
        p.setFont("Helvetica", 11)
        p.drawString(80, y - 30, risk_msg)

    p.showPage()
    p.save()
    buffer.seek(0)
    return make_response(buffer.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="report_analysis.pdf"'
    })

