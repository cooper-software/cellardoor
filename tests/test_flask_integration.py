import unittest
import json
import msgpack
from mock import Mock
import urllib
from flask import Flask
from cellardoor import errors
from cellardoor.api import API
from cellardoor.wsgi.flask_integration import create_blueprint
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


class TestResource(unittest.TestCase):
	
	def setUp(self):
		api.refresh()
		bp = create_blueprint(api)
		app = Flask(__name__)
		app.register_blueprint(bp)
		self.app = app.test_client()

		
	def test_create_fail_content_type(self):
		"""
		Create fails if the request body is not json or msgpack
		"""
		res = self.app.post(
			'/foos/',
			headers={
				'content-type': 'foo/bar'
			}
		)
		self.assertEquals(res.status.upper(), '415 Unsupported Media Type'.upper())
		
		
	def test_create_fail_validation(self):
		"""
		If validation fails, the response is a 400 error with the specific issues in the body.
		"""
		res = self.app.post(
			'/foos/',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			data=json.dumps({})
		)
		errors = json.loads(''.join(res.data))
		self.assertEquals(res.status.upper(), '400 Bad Request'.upper())
		self.assertEquals(errors, {'name':'This field is required.'})
		
		
	def test_create_fail_bad_parse(self):
		"""
		If the body can't be parsed, the response is a 400 error with the specific issues in the body.
		"""
		res = self.app.post(
			'/foos/',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			data='}{'
		)
		self.assertEquals(res.status.upper(), '400 Bad Request'.upper())
		
		
	def test_create_succeed(self):
		"""If the body matches the content type and the data passes validation, an item is created."""
		foo = {'_id':'123', 'name':'foo'}
		api.interfaces['foos'].create = Mock(return_value=foo)
		res = self.app.post(
			'/foos/',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			data=json.dumps({'name':'foo'})
		)
		created_foo = json.loads(''.join(res.data))
		self.assertEquals(created_foo, foo)
		self.assertEquals(res.status.upper(), '201 Created'.upper())
		api.interfaces['foos'].create.assert_called_with({'name':'foo'}, show_hidden=False, embedded=None, context={})
		
		
	def test_create_msgpack(self):
		foo = {'_id':'123', 'name':'foo'}
		api.interfaces['foos'].create = Mock(return_value=foo)
		res = self.app.post(
			'/foos/',
			headers={
				'accept': 'application/x-msgpack',
				'content-type': 'application/x-msgpack'
			},
			data=msgpack.packb({'name':'foo'})
		)
		created_foo = msgpack.unpackb(''.join(res.data))
		self.assertEquals(created_foo, foo)
		self.assertEquals(res.status.upper(), '201 Created'.upper())
		api.interfaces['foos'].create.assert_called_with({'name':'foo'}, show_hidden=False, embedded=None, context={})
		
		
	def test_not_found(self):
		"""If a collection raises NotFoundError, a 404 status is returned"""
		api.interfaces['foos'].get = Mock(side_effect=errors.NotFoundError())
		res = self.app.get('/foos/123')
		self.assertEquals(res.status.upper(), '404 Not Found'.upper())
		api.interfaces['foos'].get.assert_called_with('123', show_hidden=False, embedded=None, context={})
		
		
	def test_method_not_allowed(self):
		"""If attempting to use a disabled method, a 405 status is returned"""
		res = self.app.put('/bars/123')
		self.assertEquals(res.status.upper(), '405 Method Not Allowed'.upper())
		
		
	def test_forbidden(self):
		"""If authorization fails a 403 status is returned"""
		api.interfaces['foos'].get = Mock(side_effect=errors.NotAuthorizedError)
		res = self.app.get('/foos/123')
		self.assertEquals(res.status.upper(), '403 Forbidden'.upper())
		
		
	def test_unauthenticated(self):
		"""If a method is enabled but requires authentication, a 401 status is returned"""
		api.interfaces['foos'].get = Mock(side_effect=errors.NotAuthenticatedError)
		res = self.app.get('/foos/123')
		self.assertEquals(res.status.upper(), '401 Unauthorized'.upper())
		
		
	def test_disabled_field(self):
		"""If a request attempts to filter or sort by a disabled field, a 401 status is returned"""
		api.interfaces['foos'].list = Mock(side_effect=errors.DisabledFieldError)
		res = self.app.get('/foos/?%s' % urllib.urlencode({'filter':json.dumps({'name':'bob'})}))
		self.assertEquals(res.status.upper(), '401 Unauthorized'.upper())
		
		
	def test_unique_field(self):
		"""If a create request fails with a duplicate field error, a 400 status is returned"""
		api.interfaces['foos'].list = Mock(side_effect=errors.DuplicateError)
		res = self.app.get('/foos/')
		self.assertEquals(res.status.upper(), '400 Bad Request'.upper())
		
		
	def test_list(self):
		"""Will return a list of items structured by the view"""
		foos = [{'name':'foo'}, {'name':'bar'}]
		api.interfaces['foos'].list = Mock(return_value=foos)
		res = self.app.get(
			'/foos/?%s' % urllib.urlencode({
				'sort':json.dumps(['+name']),
				'filter':json.dumps({'foo':23}),
				'offset': 7,
				'limit': 10,
				'show_hidden': True
			}),
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			}
		)
		items = json.loads(''.join(res.data))
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		self.assertEquals(items, foos)
		api.interfaces['foos'].list.assert_called_with(sort=['+name'], filter={'foo':23}, offset=7, limit=10, show_hidden=True, embedded=None, context={})
		
		
	def test_get(self):
		"""A GET with a path to /collection/{id} calls colleciton.get"""
		api.interfaces['foos'].get = Mock(return_value={'_id':'123', 'name':'foo'})
		res = self.app.get('/foos/123', headers={'accept':'application/json'})
		item = json.loads(''.join(res.data))
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		self.assertEquals(item, {'name':'foo', '_id':'123'})
		api.interfaces['foos'].get.assert_called_with('123', show_hidden=False, embedded=None, context={})
		
		
	def test_update_fail_validation(self):
		"""
		If validation fails, the response is a 400 error with the specific issues in the body.
		"""
		api.interfaces['foos'].storage.get_by_id = Mock(return_value={})
		res = self.app.patch(
			'/foos/123',
			headers={
				'accept': 'application/json',
				'content-type': 'application/json'
			},
			data=json.dumps({'name':123})
		)
		
		errors = json.loads(''.join(res.data))
		self.assertEquals(res.status.upper(), '400 Bad Request'.upper())
		self.assertEquals(errors, {'name':'Expected a text value.'})
		
		
	def test_update(self):
		"""A PATCH with a path to /collection/{id} calls colleciton.update"""
		api.interfaces['foos'].update = Mock(return_value={'_id':'123', 'name':'bar'})
		res = self.app.patch(
			'/foos/123', 
			headers={
				'accept':'application/json',
				'content-type': 'application/json'
			},
			data=json.dumps({'name':'bar'})
		)
		item = json.loads(''.join(res.data))
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		self.assertEquals(item, {'name':'bar', '_id':'123'})
		api.interfaces['foos'].update.assert_called_with('123', {'name':'bar'}, show_hidden=False, embedded=None, context={})
		
		
	def test_replace(self):
		"""A PUT with a path to /collection/{id} calls colleciton.replace"""
		api.interfaces['foos'].replace = Mock(return_value={'_id':'123', 'name':'bar'})
		res = self.app.put(
			'/foos/123', 
			headers={
				'accept':'application/json',
				'content-type': 'application/json'
			},
			data=json.dumps({'name':'bar'})
		)
		item = json.loads(''.join(res.data))
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		self.assertEquals(item, {'name':'bar', '_id':'123'})
		api.interfaces['foos'].replace.assert_called_with('123', {'name':'bar'}, show_hidden=False, embedded=None, context={})
		
		
	def test_delete(self):
		"""A DELETE with a path to /collection/{id} calls collection.delete"""
		api.interfaces['foos'].delete = Mock()
		res = self.app.delete('/foos/123')
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		api.interfaces['foos'].delete.assert_called_with('123', context={})
		
		
	def test_get_single_link(self):
		"""A GET with a path to /collection/{id}/link calls collection.link"""
		api.interfaces['foos'].link = Mock(return_value={'_id':'123'})
		res = self.app.get('/foos/123/bar', headers={'accept':'application/json'})
		item = json.loads(''.join(res.data))
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		self.assertEquals(item, {'_id':'123'})
		api.interfaces['foos'].link.assert_called_with('123', 'bar', filter=None, sort=None, offset=0, limit=0, show_hidden=False, embedded=None, context={})
		
		
	def test_get_multiple_link(self):
		"""A GET with a path to /collection/{id}/link calls collection.link"""
		api.interfaces['foos'].link = Mock(return_value=[{'_id':'123'}])
		res = self.app.get(
			'/foos/123/bazes/?%s' % urllib.urlencode({
				'sort':json.dumps(['+name']),
				'filter':json.dumps({'foo':23}),
				'offset': 7,
				'limit': 10,
				'show_hidden': True
			}),
			headers={'accept':'application/json'}
		)
		items = json.loads(''.join(res.data))
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		self.assertEquals(items, [{'_id':'123'}])
		api.interfaces['foos'].link.assert_called_with('123', 'bazes', sort=['+name'], filter={'foo':23}, offset=7, limit=10, show_hidden=True, embedded=None, context={})
		
		
	def test_query_param_parse_error(self):
		"""
		Passing an unparseable query param results in a 400 error
		"""
		res = self.app.get(
			'/foos/123/bazes/?%s' % urllib.urlencode({
				'filter':'{blarg}'
			}),
			headers={'accept':'application/json'}
		)
		self.assertEquals(res.status.upper(), '400 Bad Request'.upper())
		
		
	def test_pass_identity(self):
		api.interfaces['foos'].list = Mock(return_value=[])
		environ_overrides = {'cellardoor.identity':'foo'}
		self.app.get('/foos/', environ_overrides=environ_overrides)
		api.interfaces['foos'].list.assert_called_with(sort=None, filter=None, offset=0, limit=0, show_hidden=False, embedded=None, context={'identity': 'foo'})
		
		
	def test_show_hidden(self):
		"""If show_hidden is set in the request, show_hidden=True in the collection call"""
		api.interfaces['foos'].list = Mock(return_value=None)
		api.interfaces['foos'].create = Mock(return_value=None)
		api.interfaces['foos'].get = Mock(return_value=None)
		
		res = self.app.get('/foos/?show_hidden=1')
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		res = self.app.post('/foos/?show_hidden=1', headers={'content-type':'application/json'}, data='{}')
		self.assertEquals(res.status.upper(), '201 Created'.upper())
		res = self.app.get('/foos/123?show_hidden=1')
		self.assertEquals(res.status.upper(), '200 OK'.upper())
		
		api.interfaces['foos'].list.assert_called_with(sort=None, filter=None, offset=0, limit=0, show_hidden=True, embedded=None, context={})
		api.interfaces['foos'].create.assert_called_with({}, show_hidden=True, embedded=None, context={})
		api.interfaces['foos'].get.assert_called_with('123', show_hidden=True, embedded=None, context={})
		
		
	def test_count(self):
		"""A HEAD request returns an X-Count header"""
		api.interfaces['foos'].list = Mock(return_value=52)
		res = self.app.head('/foos/')
		self.assertEquals(res.headers.get('x-count'), '52')
		api.interfaces['foos'].list.assert_called_with(sort=None, filter=None, offset=0, limit=0, show_hidden=False, embedded=None, context={}, count=True)
		
		
	def test_count_link(self):
		api.interfaces['foos'].link = Mock(return_value=52)
		res = self.app.head('/foos/123/bazes/')
		self.assertEquals(res.headers.get('x-count'), '52')
		api.interfaces['foos'].link.assert_called_with('123', 'bazes', sort=None, filter=None, offset=0, limit=0, show_hidden=False, embedded=None, context={}, count=True)
		