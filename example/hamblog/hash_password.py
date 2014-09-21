import hashlib

def hash_password(password):
	return hashlib.sha1(SALT + password).hexdigest()