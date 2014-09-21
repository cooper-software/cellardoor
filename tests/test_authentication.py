import unittest
from mock import Mock
from hammock.authentication import *


class FooIdentifier(Identifier):
	pass
	
	
class BarAuthenticator(Authenticator):
	pass


class TestAuthentication(unittest.TestCase):
	
	def test_bad_pair(self):
		self.assertRaises(ValueError, AuthenticationMiddleware, None, [('a','b')])
	
	def test_middleware(self):
		identifier = FooIdentifier()
		identifier.identify = Mock(return_value='foo')
		authenticator = BarAuthenticator()
		authenticator.authenticate = Mock(return_value='bar')
		app = Mock(return_value=[])
		middleware = AuthenticationMiddleware(app, pairs=[(identifier, authenticator)])
		environ = {'skidoo':23}
		middleware(environ, lambda: None)
		identifier.identify.assert_called_once_with(environ)
		authenticator.authenticate.assert_called_once_with('foo')
		self.assertEquals(environ, {'skidoo':23, 'hammock.identity':'bar'})