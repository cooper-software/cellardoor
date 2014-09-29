import base64
from . import Identifier
from .. import errors


class BasicAuthIdentifier(Identifier):
	"""
	Identifies Basic auth credentials in the Authorization header.
	
	The credentials take the form `{'username':'foo', 'password':'bar'}`
	"""
	type = 'Basic'
	
	def identify(self, environ):
		data = environ.get('HTTP_AUTHORIZATION')
		if not data:
			return None
		parts = data.split()
		if len(parts) != 2:
			return None
		if parts[0] != self.type:
			return None
		try:
			decoded_data = base64.standard_b64decode(parts[1])
		except TypeError:
			raise errors.IdentificationError
		else:
			try:
				username, password = decoded_data.split(':')
			except ValueError:
				raise errors.IdentificationError
			else:
				return {'username':username, 'password':password}