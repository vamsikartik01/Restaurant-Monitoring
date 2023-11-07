from app import app, db
from app.models.store_status import StoreStatus
from app.models.menu_hours import MenuHours
from app.models.timezones import Timezones
from app.models.reports import Reports
from config import config
import pandas as pd
import threading
import time

# function to handle db op/s for store_status table
def update_store_status_data(chunk_size: int):
    path = config["spreadsheets"]["store_status"]
    df = pd.read_csv(path,chunksize=chunk_size)
    for chunk in df:
        chunk['timestamp_utc'] = pd.to_datetime(chunk['timestamp_utc'], format="mixed", dayfirst=True)
        chunk = chunk.to_dict(orient='records')

        db.session.bulk_insert_mappings(StoreStatus, chunk)
        db.session.commit()

# function to handle db op/s for menu_hours table
def update_menu_hours_data(chunk_size: int):
    path = config["spreadsheets"]["menu_hours"]
    df = pd.read_csv(path,chunksize=chunk_size)
    for chunk in df:
        chunk = chunk.to_dict(orient='records')

        db.session.bulk_insert_mappings(MenuHours, chunk)
        db.session.commit()

# function to handle db op/s for timezones table
def update_timezones_data(chunk_size: int):
    path = config["spreadsheets"]["timezones"]
    df = pd.read_csv(path,chunksize=chunk_size)
    for chunk in df:
        chunk = chunk.to_dict(orient='records')

        db.session.bulk_insert_mappings(Timezones, chunk)
        db.session.commit()

# insert data from csv to db batchwise
def import_data_to_db():
    db.create_all()
    chunk_size = config['app_chunk_size']
    update_store_status_data(chunk_size=chunk_size)
    update_menu_hours_data(chunk_size=chunk_size)
    update_timezones_data(chunk_size=chunk_size)
    print("completed importing db")
    time.sleep(3600)

# start poling instance concurrently if prod config is set True
def init_poling_data():
    if config['prod']:
        thread = threading.Thread(target=import_data_to_db)
        thread.start()
