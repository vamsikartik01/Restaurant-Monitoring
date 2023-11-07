from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config

# define flask app
app = Flask(__name__)
database_config = config["database"]
database_uri = "mysql://"+database_config['username']+":"+database_config['password']+"@"+database_config["host"]+":"+database_config["port"]+"/"+database_config["database_name"]
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# update celery config
from app.celery_config import celery
celery.conf.update(app.config)

# import flask app routes
from app.routes import trigger_report, get_report, download_csv

# start the poling script concurrently
from app.services.import_data import init_poling_data
init_poling_data()