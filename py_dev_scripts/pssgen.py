import secrets
import string

# Generate a secure password
def generate_password(length=16):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

password = generate_password()
print(f"Generated password: '{password}'")
