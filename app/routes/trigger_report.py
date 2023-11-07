from app import app, db
from app.services.import_data import import_data_to_db
from app.services.ssid.ssid import generate_ssid
from app.models.reports import Reports
from app.services.reports.report import start_report
from celery import Celery

# trigger report generation concurrently
@app.route('/trigger_report', methods=['POST'])
def trigger_report():   
    report_id = generate_ssid()
    report = Reports(report_id = report_id)
    db.session.add(report)
    db.session.commit()
    start_report(report_id)
    return {"status":"success","report_id":report_id}, 200
