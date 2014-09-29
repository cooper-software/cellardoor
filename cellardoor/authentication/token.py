from .basic import BasicAuthIdentifier


class TokenAuthIdentifier(BasicAuthIdentifier):
	type = 'Token'
	
	def identify(self, environ):
		credentials = super(TokenAuthIdentifier, self).identify(environ)
		if credentials:
			return {
				'id': credentials['username'],
				'token': credentials['password']
			}