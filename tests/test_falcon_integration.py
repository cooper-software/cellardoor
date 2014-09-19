import unittest
import json
import msgpack
from mock import Mock
import urllib
from falcon.testing import TestBase
from hammock import Hammock
from hammock.integrations import add_to_falcon
from hammock.model import Entity, Text, Reference, ListOf
from hammock.collection import Collection
from hammock.methods import ALL, LIST, GET, CREATE
from hammock.views.minimal import MinimalView
from hammock import errors


class Foo(Entity):
	name = Text(required=True)
	bar = Reference('Bar')
	bazes = ListOf(Reference('Baz'))
	
	
class Bar(Entity):
	pass
	
	
class Baz(Entity):
	pass
	
	
class FoosCollection(Collection):
	entity = Foo
	links = {
		'bar': 'BarsCollection',
		'bazes': 'BazesCollection'
	}
	enabled_methods = ALL
	
	
class BarsCollection(Collection):
	entity = Bar
	enabled_methods = (LIST, GET, CREATE)
	
	
class BazesCollection(Collection):
	entity = Baz
	plural_name = 'bazes'
	enabled_methods = (LIST, GET, CREATE)


class TestResource(TestBase):
	
	def setUp(self):
		super(TestResource, self).setUp()
		self.hammock = Hammock(
			collections=(FoosCollection, BarsCollection, BazesCollection))
		add_to_falcon(self.api, self.hammock, (MinimalView(),))
		
		
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
		self.hammock.foos.create = Mock(return_value=foo)
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
		self.hammock.foos.create.assert_called_with({'name':'foo'}, show_hidden=False)
		
		
	def test_create_msgpack(self):
		foo = {'_id':'123', 'name':'foo'}
		self.hammock.foos.create = Mock(return_value=foo)
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
		self.hammock.foos.create.assert_called_with({'name':'foo'}, show_hidden=False)
		
		
	def test_not_found(self):
		"""If a collection raises NotFoundError, a 404 status is returned"""
		self.hammock.foos.get = Mock(side_effect=errors.NotFoundError())
		self.simulate_request('/foos/123', method='GET')
		self.assertEquals(self.srmock.status, '404 Not Found')
		self.hammock.foos.get.assert_called_with('123', show_hidden=False)
		
		
	def test_method_not_allowed(self):
		"""If attempting to use a disabled method, a 405 status is returned"""
		self.simulate_request('/bars/123', method="PUT")
		self.assertEquals(self.srmock.status, '405 Method Not Allowed')
		
		
	def test_forbidden(self):
		"""If authorization fails a 403 status is returned"""
		self.hammock.foos.get = Mock(side_effect=errors.NotAuthorizedError)
		self.simulate_request('/foos/123', method='GET')
		self.assertEquals(self.srmock.status, '403 Forbidden')
		
		
	def test_unauthenticated(self):
		"""If a method is enabled but requires authentication, a 401 status is returned"""
		self.hammock.foos.get = Mock(side_effect=errors.NotAuthenticatedError)
		self.simulate_request('/foos/123', method='GET')
		self.assertEquals(self.srmock.status, '401 Unauthorized')
		
		
	def test_disabled_field(self):
		"""If a request attempts to filter or sort by a disabled field, a 401 status is returned"""
		self.hammock.foos.list = Mock(side_effect=errors.DisabledFieldError)
		self.simulate_request('/foos', query_string=urllib.urlencode({'filter':json.dumps({'name':'bob'})}))
		self.assertEquals(self.srmock.status, '401 Unauthorized')
		
		
	def test_unique_field(self):
		"""If a create request fails with a duplicate field error, a 400 status is returned"""
		self.hammock.foos.list = Mock(side_effect=errors.DuplicateError)
		self.simulate_request('/foos')
		self.assertEquals(self.srmock.status, '400 Bad Request')
		
		
	def test_list(self):
		"""Will return a list of items structured by the view"""
		foos = [{'name':'foo'}, {'name':'bar'}]
		self.hammock.foos.list = Mock(return_value=foos)
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
		self.assertEquals(result, {'items':foos})
		self.hammock.foos.list.assert_called_with(sort=['+name'], filter={'foo':23}, offset=7, limit=10, show_hidden=True)
		
		
	def test_get(self):
		"""A GET with a path to /collection/{id} calls colleciton.get"""
		self.hammock.foos.get = Mock(return_value={'_id':'123', 'name':'foo'})
		data = self.simulate_request('/foos/123', method='GET', headers={'accept':'application/json'})
		result = json.loads(''.join(data))
		self.assertEquals(self.srmock.status, '200 OK')
		self.assertEquals(result, {'name':'foo', '_id':'123'})
		self.hammock.foos.get.assert_called_with('123', show_hidden=False)
		
		
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
		self.hammock.foos.update = Mock(return_value={'_id':'123', 'name':'bar'})
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
		self.hammock.foos.update.assert_called_with('123', {'name':'bar'}, show_hidden=False)
		
		
	def test_replace(self):
		"""A PUT with a path to /collection/{id} calls colleciton.replace"""
		self.hammock.foos.replace = Mock(return_value={'_id':'123', 'name':'bar'})
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
		self.hammock.foos.replace.assert_called_with('123', {'name':'bar'}, show_hidden=False)
		
		
	def test_delete(self):
		"""A DELETE with a path to /collection/{id} calls collection.delete"""
		self.hammock.foos.delete = Mock()
		self.simulate_request('/foos/123', method='DELETE')
		self.assertEquals(self.srmock.status, '200 OK')
		self.hammock.foos.delete.assert_called_with('123')
		
		
	def test_get_single_link(self):
		"""A GET with a path to /collection/{id}/link calls collection.link"""
		self.hammock.foos.link = Mock(return_value={'_id':'123'})
		data = self.simulate_request('/foos/123/bar', method='GET', headers={'accept':'application/json'})
		result = json.loads(''.join(data))
		self.assertEquals(self.srmock.status, '200 OK')
		self.assertEquals(result, {'_id':'123'})
		self.hammock.foos.link.assert_called_with('123', 'bar', filter=None, sort=None, offset=0, limit=0, show_hidden=False)
		
		
	def test_get_multiple_link(self):
		"""A GET with a path to /collection/{id}/link calls collection.link"""
		self.hammock.foos.link = Mock(return_value={'_id':'123'})
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
		self.hammock.foos.link.assert_called_with('123', 'bazes', sort=['+name'], filter={'foo':23}, offset=7, limit=10, show_hidden=True)