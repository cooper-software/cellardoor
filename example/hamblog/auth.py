import falcon
import hashlib
import json
import os
import binascii
from datetime import datetime, timedelta
from hammock.auth import TokenAuthenticator
from hammock import errors
from .storage import storage


token_life = timedelta(days=30)


def hash_password(password):
	return hashlib.sha1('%s%s' % (self.SALT, password)).hexdigest()


def get_identity(token):
	person = storage.get('people', filter={'token.value': token})
	if person:
		if is_token_expired(person['token']):
			raise errors.NotAuthenticated, "Token expired"
		else:
			now = datetime.utcnow()
			if person['token']['expires'] - now < timedelta(hours=12):
				person['token']['expires'] = now + token_life
				storage.save('people', person)
			return person
	
	
def is_token_expired(token):
	return token['expires'] <= datetime.utcnow()
	
	
def create_token(person):
	random_string = binascii.b2a_hex(os.urandom(10))
	return {
		'expires': datetime.utcnow() + token_life,
		'value': hashlib.sha1('%s:%s' % (person['_id'], random_string)).hexdigest()
	}
	
	
	
token_auth = TokenAuthenticator(identity_provider=setup_identity)


class LoginResource(object):
	
	SALT = 'df(*&D*d7futeurfywegrfIU&TDF^YTdfew76rtf'
	
	def on_post(self, req, resp):
		try:
			data = json.load(req.stream)
		except ValueError:
			raise falcon.HTTPError(
				falcon.HTTP_753,
				'Malformed JSON',
				'Could not decode the request body.'
			)
		
		if 'email' not in data or 'password' not in data:
			raise falcon.HTTPError(
				falcon.HTTP_422,
				'Unprocessable Entity',
				'Missing email or password field.'
			)
			
		filter={'email':data['email'], 'password':hash_password(data['password'])}
		person = storage.get('people', filter=filter)
		
		if not person:
			raise falcon.HTTPForbidden
			
		if 'token' not in person or is_token_expired(person['token']):
			person['token'] = create_token()
		else:
			person['token']['expires'] = datetime.utcnow()
			
		storage.save('people', person)
		
		resp.status = falcon.HTTP_200
		resp.body = json.dumps(person['token'])
		