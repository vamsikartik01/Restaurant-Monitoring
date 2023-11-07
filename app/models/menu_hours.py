from app import app, db

class MenuHours(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    store_id = db.Column(db.String(255), nullable= False)
    day = db.Column(db.Integer, nullable=False)
    start_time_local = db.Column(db.Time, nullable=False)
    end_time_local = db.Column(db.Time, nullable=False)

    def __init__(self, store_id, day, start_time_local, end_time_local):
        self.store_id = store_id
        self.day = day
        self.start_time_local = start_time_local
        self.end_time_local = end_time_local