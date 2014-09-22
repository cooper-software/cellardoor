from cellardoor.authentication import Authenticator
from .storage import storage
from .model import Person
from .hash_password import hash_password

SALT = 'change-me'

class UsernamePasswordAuthenticator(Authenticator):
	
	def authenticate(self, credentials):
		username = credentials.get('username', '')
		password = hash_password( credentials.get('password', '') )
		results = list(storage.get(Person, filter={'username':username, 'password':password}), limit=1)
		if len(results) == 0:
			return None
		return results[0]
		
		
