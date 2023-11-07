from app import app, db
from app.models.reports import Reports
from flask import jsonify
from config import config

# send report generation status as response
@app.route('/get_report/<string:report_id>', methods=['GET'])
def get_report(report_id):
    report = Reports.query.filter_by(report_id = report_id).first()
    json_response = jsonify({"report_id":report.report_id, "status":report.status})
    if report.status == "Completed":
        url = config['app_host']+"/download/"+report_id
        json_response = jsonify({"report_id":report.report_id, "status":report.status, "download_url":url})
    
    return json_response, 200