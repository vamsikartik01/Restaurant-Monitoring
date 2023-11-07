import string
import secrets

# generate random ssid of length 16
def generate_ssid():
    length = 16
    character_set = string.ascii_letters + string.digits
    sid = ''.join(secrets.choice(character_set) for _ in range(length))
    return sid