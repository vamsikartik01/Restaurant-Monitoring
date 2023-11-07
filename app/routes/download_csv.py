from app import app, db
from app.models.reports import Reports
from flask import jsonify, send_file, make_response

# send the report.csv file as a response
@app.route('/download/<string:report_id>', methods=['GET'])
def download_csv(report_id):
    csv_path = "../reports/"+report_id+".csv"
    return send_file(csv_path, as_attachment=True)