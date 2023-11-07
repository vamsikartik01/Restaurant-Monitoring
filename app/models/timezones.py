from app import app, db

class Timezones(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String(255), nullable=False)
    timezone_str = db.Column(db.String(255))

    def __init__(self, store_id, timezone_str):
        self.store_id = store_id
        self.timezone_str = timezone_str