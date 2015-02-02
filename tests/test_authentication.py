import unittest
from mock import Mock
import base64
from cellardoor import errors
from cellardoor.authentication import *
from cellardoor.authentication.basic import BasicAuthIdentifier


class FooIdentifier(Identifier):
	pass
	
	
class BarAuthenticator(Authenticator):
	pass


class TestAuthentication(unittest.TestCase):
	
	def test_abstract_identifier(self):
		id = Identifier()
		with self.assertRaises(NotImplementedError):
			id.identify({})
			
	def test_abstract_authenticator(self):
		auth = Authenticator()
		with self.assertRaises(NotImplementedError):
			auth.authenticate({})
	
	def test_bad_identifier(self):
		self.assertRaises(ValueError, AuthenticationMiddleware, None, [(None, BarAuthenticator())])
		
	def test_bad_authenticator(self):
		self.assertRaises(ValueError, AuthenticationMiddleware, None, [(FooIdentifier(), None)])
	
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
		self.assertEquals(environ, {'skidoo':23, 'cellardoor.identity':'bar'})
		
	def test_middleware_skip(self):
		id_one = FooIdentifier()
		id_one.identify = Mock(return_value=None)
		id_two = FooIdentifier()
		id_two.identify = Mock(return_value='two')
		id_three = FooIdentifier()
		id_three.identify = Mock(return_value='three')
		auth_one = BarAuthenticator()
		auth_one.authenticate = Mock(return_value='one')
		auth_two = BarAuthenticator()
		auth_two.authenticate = Mock(return_value='two')
		auth_three = BarAuthenticator()
		auth_three.authenticate = Mock(return_value='three')
		app = Mock(return_value=[])
		
		middleware = AuthenticationMiddleware(
			app, 
			pairs=[
				(id_one, auth_one),
				(id_two, auth_two),
				(id_three, auth_three)
			]
		)
		
		environ = {}
		middleware(environ, lambda: None)
		self.assertEquals(environ, {'cellardoor.identity':'two'})
		

class TestBasic(unittest.TestCase):
	
	def test_skip_if_no_auth_header(self):
		identifier = BasicAuthIdentifier()
		credentials = identifier.identify({})
		self.assertEquals(credentials, None)
		
		
	def test_skip_if_not_basic(self):
		identifier = BasicAuthIdentifier()
		credentials = identifier.identify({'HTTP_AUTHORIZATION':'Foo 123'})
		self.assertEquals(credentials, None)
		
		
	def test_error_if_not_base64(self):
		identifier = BasicAuthIdentifier()
		with self.assertRaises(errors.IdentificationError):
			identifier.identify({'HTTP_AUTHORIZATION':'Basic \x000'})
		
		
	def test_error_if_malformed(self):
		identifier = BasicAuthIdentifier()
		credentials = base64.standard_b64encode('foobar')
		with self.assertRaises(errors.IdentificationError):
			identifier.identify({'HTTP_AUTHORIZATION':'Basic %s' % credentials})
			
			
	def test_pass(self):
		identifier = BasicAuthIdentifier()
		credentials = base64.standard_b64encode('foo:bar')
		identified_credentials = identifier.identify({'HTTP_AUTHORIZATION':'Basic %s' % credentials})
		self.assertEquals(identified_credentials, {'username':'foo', 'password':'bar'})
		