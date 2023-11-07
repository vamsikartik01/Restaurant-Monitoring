import json

def load_config():
    with open('config.json', 'r') as file:
        config = json.load(file)

    return config
    
# load config from from config.json file
config = load_config()