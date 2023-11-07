from celery import Celery
from config import config
import time

redis_config = config["redis"]
database_config = config["database"]

# celery instance config
celery = Celery(
    'loop-app',
    broker="redis://"+redis_config["host"]+":"+redis_config['port']+"/0",
    backend = "db+mysql://"+database_config['username']+":"+database_config['password']+"@"+database_config["host"]+":"+database_config["port"]+"/"+database_config["database_name"],
)