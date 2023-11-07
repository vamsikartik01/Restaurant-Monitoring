from app import app, db

class StoreStatus(db.Model):
    id = db.Column(db.Integer, primary_key= True)
    store_id = db.Column(db.String(255), nullable= False)
    status = db.Column(db.String(50), nullable= False)
    timestamp_utc = db.Column(db.TIMESTAMP, nullable= False)

    def __init__(self, store_id, status, timestamp_utc):
        self.store_id = store_id
        self.status = status
        self.timestamp_utc = timestamp_utc