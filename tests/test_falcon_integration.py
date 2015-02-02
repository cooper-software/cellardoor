import unittest
import json
import msgpack
from mock import Mock
import urllib
from falcon.testing import TestBase, create_environ
from cellardoor import errors
from cellardoor.api import API
from cellardoor.wsgi.falcon_app import FalconApp
from cellardoor.model import Model, Entity, Text, Link, ListOf
from cellardoor.storage import Storage
from cellardoor.api.interface import ALL, LIST, GET, CREATE


model = Model(storage=Storage())
api  = API(model)


class Foo(model.Entity):
	name = Text(required=True)
	bar = Link('Bar')
	bazes = ListOf(Link('Baz'))
	
	
class Bar(model.Entity):
	pass
	
	
class Baz(model.Entity):
	pass

	
class Foos(api.Interface):
	entity = Foo
	method_authorization = {
		ALL: None
	}
	
	
class Bars(api.Interface):
	entity = Bar
	method_authorization = {
		(LIST, GET, CREATE): None
	}
	
	
class Bazes(api.Interface):
	entity = Baz
	plural_name = 'bazes'
	method_authorization = {
		(LIST, GET, CREATE): None
	}


class TestResource(TestBase):
	
	def setUp(self):
		super(TestResource, self).setUp()
		api.refresh()
		FalconApp(api, falcon_app=self.api)
	
	
	def test_fail_no_methods(self):
		model = Model(storage=Mock())
		
		class Foo(model.Entity):
			pass
		
		empty_api = API(model)
		
		class Foos(empty_api.Interface):
			entity = Foo
			
		self.assertRaises(Exception, FalconApp, empty_api)

		
	def test_create_fail_content_type(self):
		"""
		Create fails if the request body is not json or msgpack
		"""
		self.simulate_request(
			'/foos',
			method='POST',
			headers={
				'content-type': 'foo/bar'
			}
		)
		self.assertEquals(self.srmock.status, '415 Unsupported Media Type')
		
		
	def test_create_fail_validation(self):
		"""
		If validation fails, the response is a 400 error with the specific issues in the body.
		"""
		result = self.simulate_request(
			'/foos',
			method='POST',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			body=json.dumps({})
		)
		errors = json.loads(''.join(result))
		self.assertEquals(self.srmock.status, '400 Bad Request')
		self.assertEquals(errors, {'name':'This field is required.'})
		
		
	def test_create_fail_bad_parse(self):
		"""
		If the body can't be parsed, the response is a 400 error with the specific issues in the body.
		"""
		result = self.simulate_request(
			'/foos',
			method='POST',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			body='}{'
		)
		self.assertEquals(self.srmock.status, '400 Bad Request')
		
		
	def test_create_succeed(self):
		"""If the body matches the content type and the data passes validation, an item is created."""
		foo = {'_id':'123', 'name':'foo'}
		api.interfaces['foos'].create = Mock(return_value=foo)
		result = self.simulate_request(
			'/foos',
			method='POST',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			body=json.dumps({'name':'foo'})
		)
		created_foo = json.loads(''.join(result))
		self.assertEquals(created_foo, foo)
		self.assertEquals(self.srmock.status, '201 Created')
		api.interfaces['foos'].create.assert_called_with({'name':'foo'}, show_hidden=False, embedded=None, context={})
		
		
	def test_create_msgpack(self):
		foo = {'_id':'123', 'name':'foo'}
		api.interfaces['foos'].create = Mock(return_value=foo)
		result = self.simulate_request(
			'/foos',
			method='POST',
			headers={
				'accept': 'application/x-msgpack',
				'content-type': 'application/x-msgpack'
			},
			body=msgpack.packb({'name':'foo'})
		)
		created_foo = msgpack.unpackb(''.join(result))
		self.assertEquals(created_foo, foo)
		self.assertEquals(self.srmock.status, '201 Created')
		api.interfaces['foos'].create.assert_called_with({'name':'foo'}, show_hidden=False, embedded=None, context={})
		
		
	def test_not_found(self):
		"""If a collection raises NotFoundError, a 404 status is returned"""
		api.interfaces['foos'].get = Mock(side_effect=errors.NotFoundError())
		self.simulate_request('/foos/123', method='GET')
		self.assertEquals(self.srmock.status, '404 Not Found')
		api.interfaces['foos'].get.assert_called_with('123', show_hidden=False, embedded=None, context={})
		
		
	def test_method_not_allowed(self):
		"""If attempting to use a disabled method, a 405 status is returned"""
		self.simulate_request('/bars/123', method="PUT")
		self.assertEquals(self.srmock.status, '405 Method Not Allowed')
		
		
	def test_forbidden(self):
		"""If authorization fails a 403 status is returned"""
		api.interfaces['foos'].get = Mock(side_effect=errors.NotAuthorizedError)
		self.simulate_request('/foos/123', method='GET')
		self.assertEquals(self.srmock.status, '403 Forbidden')
		
		
	def test_unauthenticated(self):
		"""If a method is enabled but requires authentication, a 401 status is returned"""
		api.interfaces['foos'].get = Mock(side_effect=errors.NotAuthenticatedError)
		self.simulate_request('/foos/123', method='GET')
		self.assertEquals(self.srmock.status, '401 Unauthorized')
		
		
	def test_disabled_field(self):
		"""If a request attempts to filter or sort by a disabled field, a 401 status is returned"""
		api.interfaces['foos'].list = Mock(side_effect=errors.DisabledFieldError)
		self.simulate_request('/foos', query_string=urllib.urlencode({'filter':json.dumps({'name':'bob'})}))
		self.assertEquals(self.srmock.status, '401 Unauthorized')
		
		
	def test_unique_field(self):
		"""If a create request fails with a duplicate field error, a 400 status is returned"""
		api.interfaces['foos'].list = Mock(side_effect=errors.DuplicateError)
		self.simulate_request('/foos')
		self.assertEquals(self.srmock.status, '400 Bad Request')
		
		
	def test_list(self):
		"""Will return a list of items structured by the view"""
		foos = [{'name':'foo'}, {'name':'bar'}]
		api.interfaces['foos'].list = Mock(return_value=foos)
		data = self.simulate_request(
			'/foos',
			method='GET',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			query_string=urllib.urlencode({
				'sort':json.dumps(['+name']),
				'filter':json.dumps({'foo':23}),
				'offset': 7,
				'limit': 10,
				'show_hidden': True
			})
		)
		result = json.loads(''.join(data))
		self.assertEquals(self.srmock.status, '200 OK')
		self.assertEquals(result, foos)
		api.interfaces['foos'].list.assert_called_with(sort=['+name'], filter={'foo':23}, offset=7, limit=10, show_hidden=True, embedded=None, context={})
		
		
	def test_get(self):
		"""A GET with a path to /collection/{id} calls colleciton.get"""
		api.interfaces['foos'].get = Mock(return_value={'_id':'123', 'name':'foo'})
		data = self.simulate_request('/foos/123', method='GET', headers={'accept':'application/json'})
		result = json.loads(''.join(data))
		self.assertEquals(self.srmock.status, '200 OK')
		self.assertEquals(result, {'name':'foo', '_id':'123'})
		api.interfaces['foos'].get.assert_called_with('123', show_hidden=False, embedded=None, context={})
		
		
	def test_update_fail_validation(self):
		"""
		If validation fails, the response is a 400 error with the specific issues in the body.
		"""
		result = self.simulate_request(
			'/foos/123',
			method='PUT',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			body=json.dumps({'name':123})
		)
		
		errors = json.loads(''.join(result))
		self.assertEquals(self.srmock.status, '400 Bad Request')
		self.assertEquals(errors, {'name':'Expected a text value.'})
		
		
	def test_update(self):
		"""A PATCH with a path to /collection/{id} calls colleciton.update"""
		api.interfaces['foos'].update = Mock(return_value={'_id':'123', 'name':'bar'})
		data = self.simulate_request(
			'/foos/123', 
			method='PATCH', 
			headers={
				'accept':'application/json',
				'content-type': 'application/json'
			},
			body=json.dumps({'name':'bar'})
			)
		result = json.loads(''.join(data))
		self.assertEquals(self.srmock.status, '200 OK')
		self.assertEquals(result, {'name':'bar', '_id':'123'})
		api.interfaces['foos'].update.assert_called_with('123', {'name':'bar'}, show_hidden=False, embedded=None, context={})
		
		
	def test_replace(self):
		"""A PUT with a path to /collection/{id} calls colleciton.replace"""
		api.interfaces['foos'].replace = Mock(return_value={'_id':'123', 'name':'bar'})
		data = self.simulate_request(
			'/foos/123', 
			method='PUT', 
			headers={
				'accept':'application/json',
				'content-type': 'application/json'
			},
			body=json.dumps({'name':'bar'})
			)
		result = json.loads(''.join(data))
		self.assertEquals(self.srmock.status, '200 OK')
		self.assertEquals(result, {'name':'bar', '_id':'123'})
		api.interfaces['foos'].replace.assert_called_with('123', {'name':'bar'}, show_hidden=False, embedded=None, context={})
		
		
	def test_delete(self):
		"""A DELETE with a path to /collection/{id} calls collection.delete"""
		api.interfaces['foos'].delete = Mock()
		self.simulate_request('/foos/123', method='DELETE')
		self.assertEquals(self.srmock.status, '200 OK')
		api.interfaces['foos'].delete.assert_called_with('123', context={})
		
		
	def test_get_single_link(self):
		"""A GET with a path to /collection/{id}/link calls collection.link"""
		api.interfaces['foos'].link = Mock(return_value={'_id':'123'})
		data = self.simulate_request('/foos/123/bar', method='GET', headers={'accept':'application/json'})
		result = json.loads(''.join(data))
		self.assertEquals(self.srmock.status, '200 OK')
		self.assertEquals(result, {'_id':'123'})
		api.interfaces['foos'].link.assert_called_with('123', 'bar', filter=None, sort=None, offset=0, limit=0, show_hidden=False, embedded=None, context={})
		
		
	def test_get_multiple_link(self):
		"""A GET with a path to /collection/{id}/link calls collection.link"""
		api.interfaces['foos'].link = Mock(return_value={'_id':'123'})
		data = self.simulate_request(
			'/foos/123/bazes', 
			method='GET', 
			headers={'accept':'application/json'},
			query_string=urllib.urlencode({
				'sort':json.dumps(['+name']),
				'filter':json.dumps({'foo':23}),
				'offset': 7,
				'limit': 10,
				'show_hidden': True
			})
		)
		result = json.loads(''.join(data))
		self.assertEquals(self.srmock.status, '200 OK')
		self.assertEquals(result, {'_id':'123'})
		api.interfaces['foos'].link.assert_called_with('123', 'bazes', sort=['+name'], filter={'foo':23}, offset=7, limit=10, show_hidden=True, embedded=None, context={})
		
		
	def test_pass_identity(self):
		api.interfaces['foos'].list = Mock(return_value=[])
		environ = create_environ('/foos')
		environ['cellardoor.identity'] = 'foo'
		self.api(environ, lambda *args, **kwargs: [])
		api.interfaces['foos'].list.assert_called_with(sort=None, filter=None, offset=0, limit=0, show_hidden=False, embedded=None, context={'identity': 'foo'})
		
		
	def test_show_hidden(self):
		"""If show_hidden is set in the request, show_hidden=True in the collection call"""
		api.interfaces['foos'].list = Mock(return_value=None)
		api.interfaces['foos'].create = Mock(return_value=None)
		api.interfaces['foos'].get = Mock(return_value=None)
		
		self.simulate_request('/foos', query_string='show_hidden=1')
		self.assertEquals(self.srmock.status, '200 OK')
		self.simulate_request('/foos', method='POST', headers={'content-type':'application/json'}, body='{}', query_string='show_hidden=1')
		self.assertEquals(self.srmock.status, '201 Created')
		self.simulate_request('/foos/123', query_string='show_hidden=1')
		self.assertEquals(self.srmock.status, '200 OK')
		
		api.interfaces['foos'].list.assert_called_with(sort=None, filter=None, offset=0, limit=0, show_hidden=True, embedded=None, context={})
		api.interfaces['foos'].create.assert_called_with({}, show_hidden=True, embedded=None, context={})
		api.interfaces['foos'].get.assert_called_with('123', show_hidden=True, embedded=None, context={})
		
		
	def test_count(self):
		"""A HEAD request returns an X-Count header"""
		api.interfaces['foos'].list = Mock(return_value=52)
		self.simulate_request('/foos', method='HEAD')
		self.assertEquals(self.srmock.headers_dict['x-count'], '52')
		api.interfaces['foos'].list.assert_called_with(sort=None, filter=None, offset=0, limit=0, show_hidden=False, embedded=None, context={}, count=True)
		
		
	def test_count_link(self):
		api.interfaces['foos'].link = Mock(return_value=52)
		self.simulate_request('/foos/123/bazes', method='HEAD')
		self.assertEquals(self.srmock.headers_dict['x-count'], '52')
		api.interfaces['foos'].link.assert_called_with('123', 'bazes', sort=None, filter=None, offset=0, limit=0, show_hidden=False, embedded=None, context={}, count=True)
		