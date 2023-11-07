from app import app, db
from datetime import datetime

class Reports(db.Model):
    id = db.Column(db.Integer, primary_key= True)
    report_id = db.Column(db.String(255), nullable= False)
    status = db.Column(db.String(50), nullable= False)
    created_at = db.Column(db.TIMESTAMP,  default=datetime.utcnow, nullable= False)
    completed_at = db.Column(db.TIMESTAMP)

    def __init__(self, report_id):
        self.report_id = report_id
        self.status = "Running"

    def complete(self):
        self.status = "Completed"
        self.completed_at = datetime.utcnow()

    def failed(self):
        self.status = "Failed"
        self.completed_at = datetime.utcnow()