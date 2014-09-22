from .. import errors


class AuthenticationMiddleware(object):
	
	def __init__(self, app, pairs=[]):
		self.app = app
		
		for x,y in pairs:
			if not isinstance(x, Identifier):
				raise ValueError, "Expected first item in pair to be an instance of Identifier"
			if not isinstance(y, Authenticator):
				raise ValueError, "Expected second item in pair to be an instance of Authenticator"
			
		self.pairs = pairs
			
		
		
	def __call__(self, environ, start_response):
		identity = None
		for identifier, authenticator in self.pairs:
			credentials = identifier.identify(environ)
			if credentials:
				identity = authenticator.authenticate(credentials)
				break
		environ['cellardoor.identity'] = identity
		return self.app(environ, start_response)
		
		
		
class Identifier(object):
	
	def identify(self, environ):
		raise NotImplementedError
		
		
		
class Authenticator(object):
	
	def authenticate(self, credentials):
		raise NotImplementedError
		
		