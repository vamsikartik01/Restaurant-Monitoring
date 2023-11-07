from app import app
from config import config

if __name__ == "__main__" :
    print("Restaurant Monitoring Started!")
    app.run(debug=config['debug'])