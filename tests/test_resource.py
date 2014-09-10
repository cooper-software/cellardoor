import unittest
import json
from falcon.testing import TestBase
from hammock.model import Model, Entity, Reference, Link, Text, ListOf
from hammock.resource import Resource
from hammock.methods import ALL
from hammock.storage.mongodb import MongoDBStorage
from hammock.views.minimal import MinimalView
from hammock import Hammock
from bson.objectid import ObjectId


storage = MongoDBStorage('test')


class Foo(Entity):
	stuff = Text(required=True)
	optional_stuff = Text()
	bars = Link('Bar', 'foo')
	bazes = ListOf(Reference('Baz', storage=storage))
	
	
class Bar(Entity):
	foo = Reference(Foo, storage=storage, embedded=True)
	bazes = ListOf(Reference('Baz', storage=storage, embedded=True))
	
	
class Baz(Entity):
	name = Text(required=True)
	foo = Link(Foo, 'bazes', multiple=False)
	

class FoosResource(Resource):
	entity = Foo
	enabled_methods = ALL
	link_resources = {
		'bars': 'BarsResource',
		'bazes': 'BazesResource'
	}
	
	
class BarsResource(Resource):
	entity = Bar
	enabled_methods = ALL
	link_resources = {
		'foo': FoosResource,
		'bazes': 'BazesResource'
	}
	
	
class BazesResource(Resource):
	entity = Baz
	plural_name = 'bazes'
	enabled_methods = ALL
	link_resources = {
		'foo': FoosResource
	}
	

model = Model(Foo, Bar, Baz)
storage.set_model(model)

class ResourceTest(TestBase):
	
	def setUp(self):
		for c in storage.db.collection_names():
			if not c.startswith('system.'):
				storage.db[c].drop()
		super(ResourceTest, self).setUp()
				
	
	def test_add_collection_to_api(self):
		"""
		A resource should add routes for the collection methods
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		self.simulate_request('/foos')
		self.assertEquals(self.srmock.status, '200 OK')
		self.simulate_request('/foos', method='POST')
		self.assertNotEquals(self.srmock.status, '404 Not Found')
		self.simulate_request('/foos', method='PUT')
		self.assertEquals(self.srmock.status, '405 Method Not Allowed')
		self.simulate_request('/foos', method='PATCH')
		self.assertEquals(self.srmock.status, '405 Method Not Allowed')
		self.simulate_request('/foos', method='DELETE')
		self.assertEquals(self.srmock.status, '405 Method Not Allowed')
		
		
	def test_add_individual_to_api(self):
		"""
		A resource should add routes for the individual methods
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		fake_id = str(ObjectId())
		self.simulate_request('/foos/%s' % fake_id)
		self.assertNotEquals(self.srmock.status, '405 Method Not Allowed')
		self.simulate_request('/foos/%s' % fake_id, method='POST')
		self.assertEquals(self.srmock.status, '405 Method Not Allowed')
		self.simulate_request('/foos/%s' % fake_id, method='PUT')
		self.assertNotEquals(self.srmock.status, '405 Method Not Allowed')
		self.simulate_request('/foos/%s' % fake_id, method='PATCH')
		self.assertNotEquals(self.srmock.status, '405 Method Not Allowed')
		self.simulate_request('/foos/%s' % fake_id, method='DELETE')
		self.assertNotEquals(self.srmock.status, '405 Method Not Allowed')
		
		
	def test_create_fail_content_type(self):
		"""
		Fails if the request doesn't specify an application/json or 
		application/x-msgpack content type
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		self.simulate_request('/foos', method='POST')
		self.assertEquals(self.srmock.status, '415 Unsupported Media Type')
		self.simulate_request('/foos', method='POST', headers={'content-type':'text/plain'})
		self.assertEquals(self.srmock.status, '415 Unsupported Media Type')
		
		
	def test_create_fail_invalid_data(self):
		"""
		Fails if the request fields don't pass validation.
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		self.simulate_request('/foos', method='POST', headers={'content-type':'application/json'}, body=json.dumps({}))
		self.assertEquals(self.srmock.status, '400 Bad Request')
		
		
	def test_create_succeed(self):
		"""
		Creates a record in persistent storage if we pass validation.
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo'}))
		
		self.assertEquals(self.srmock.status, '201 Created')
		data = ''.join(result)
		obj = json.loads(data)
		self.assertIn('id', obj)
		obj_id = obj['id']
		del obj['id']
		self.assertEquals(obj, {'stuff':'foo'})
		
		
	def test_get_succeed(self):
		"""
		Returns a list of created items
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo'}))
		self.assertEquals(self.srmock.status, '201 Created')
		data = ''.join(result)
		obj = json.loads(data)
		result = self.simulate_request('/foos', headers={'accept':'application/json'})
		self.assertEquals(self.srmock.status, '200 OK')
		data = ''.join(result)
		objs = json.loads(data)
		self.assertEquals(objs, {'items':[obj]})
		
		
	def test_patch(self):
		"""
		Can update a subset of fields
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo', 'optional_stuff':'bar'}))
		data = ''.join(result)
		obj = json.loads(data)
		result = self.simulate_request('/foos/%s' % obj['id'], 
			                           method='PATCH', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'baz'}))
		self.assertEquals(self.srmock.status, '200 OK')
		data = ''.join(result)
		updated_obj = json.loads(data)
		self.assertEquals(updated_obj, {'id':obj['id'], 'stuff':'baz', 'optional_stuff':'bar'})
		
		
	def test_put(self):
		"""
		Can replace a whole existing item
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo', 'optional_stuff':'bar'}))
		data = ''.join(result)
		obj = json.loads(data)
		result = self.simulate_request('/foos/%s' % obj['id'], 
			                           method='PUT', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'baz'}))
		self.assertEquals(self.srmock.status, '200 OK')
		data = ''.join(result)
		updated_obj = json.loads(data)
		self.assertEquals(updated_obj, {'id':obj['id'], 'stuff':'baz'})
		
		
	def test_delete(self):
		"""
		Can remove an existing item
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo', 'optional_stuff':'bar'}))
		data = ''.join(result)
		obj = json.loads(data)
		self.simulate_request('/foos/%s' % obj['id'], method='DELETE')
		result = self.simulate_request('/foos/%s' % obj['id'], headers={'accept':'application/json'})
		self.assertEquals(self.srmock.status, '404 Not Found')
		
		
	def test_single_reference_validation_fail(self):
		"""
		Fails validation if a reference doesn't actually exist.
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/bars', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'foo':str(ObjectId())}))
		self.assertEquals(self.srmock.status, '400 Bad Request')
		
		
	def test_single_reference_set(self):
		"""
		Can set a reference by passing in the ID of an existing item.
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo', 'optional_stuff':'bar'}))
		self.assertEquals(self.srmock.status, '201 Created')
		data = ''.join(result)
		obj = json.loads(data)
		self.simulate_request('/bars', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'foo':obj['id']}))
		self.assertEquals(self.srmock.status, '201 Created')
		
		
	def test_single_reference_get(self):
		"""
		Can get a reference through a link.
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo', 'optional_stuff':'bar'}))
		self.assertEquals(self.srmock.status, '201 Created')
		data = ''.join(result)
		foo = json.loads(data)
		result = self.simulate_request('/bars', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'foo':foo['id']}))
		data = ''.join(result)
		bar = json.loads(data)
		self.assertEquals(self.srmock.status, '201 Created')
		result = self.simulate_request('/bars/%s/foo' % bar['id'], headers={'accept': 'application/json'})
		data = ''.join(result)
		linked_foo = json.loads(data)
		self.assertEquals(linked_foo, foo)
		
		
	def test_single_reference_get_embedded(self):
		"""
		Embedded references are included when fetching the referencing item.
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo', 'optional_stuff':'bar'}))
		self.assertEquals(self.srmock.status, '201 Created')
		data = ''.join(result)
		foo = json.loads(data)
		result = self.simulate_request('/bars', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'foo':foo['id']}))
		data = ''.join(result)
		bar = json.loads(data)
		self.assertEquals(self.srmock.status, '201 Created')
		self.assertEquals(bar, {'foo':foo, 'id':bar['id']})
		
		
	def test_multiple_reference_set(self):
		"""
		Can set a list of references when creating an item
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		
		baz_ids = []
		
		for i in range(0,3):
			result = self.simulate_request('/bazes', 
				                           method='POST', 
				                           headers={
				                           	  'content-type':'application/json',
				                           	  'accept': 'application/json'
				                           }, 
				                           body=json.dumps({'name':'Baz#%d' % i}))
			data = ''.join(result)
			obj = json.loads(data)
			baz_ids.append(obj['id'])
			
		self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'things', 'bazes':baz_ids}))
		self.assertEquals(self.srmock.status, '201 Created')
		
		
	def test_multiple_reference_get(self):
		"""
		Can get a list of references through a link
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		
		bazes = []
		
		for i in range(0,3):
			result = self.simulate_request('/bazes', 
				                           method='POST', 
				                           headers={
				                           	  'content-type':'application/json',
				                           	  'accept': 'application/json'
				                           }, 
				                           body=json.dumps({'name':'Baz#%d' % i}))
			data = ''.join(result)
			obj = json.loads(data)
			bazes.append(obj)
			
		baz_ids = [x['id'] for x in bazes]
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff': 'things', 'bazes':baz_ids}))
		
		data = ''.join(result)
		foo = json.loads(data)
		
		result = self.simulate_request('/foos/%s/bazes' % foo['id'], headers={'accept': 'application/json'})
		data = ''.join(result)
		linked_bazes = json.loads(data)
		self.assertEquals(linked_bazes, {'items':bazes})
		
		
	def test_multiple_reference_get_embedded(self):
		"""
		Embedded reference list is included when fetching the referencing item.
		"""
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		
		bazes = []
		
		for i in range(0,3):
			result = self.simulate_request('/bazes', 
				                           method='POST', 
				                           headers={
				                           	  'content-type':'application/json',
				                           	  'accept': 'application/json'
				                           }, 
				                           body=json.dumps({'name':'Baz#%d' % i}))
			data = ''.join(result)
			obj = json.loads(data)
			bazes.append(obj)
			
		baz_ids = [x['id'] for x in bazes]
		result = self.simulate_request('/bars', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'bazes':baz_ids}))
		
		data = ''.join(result)
		bar = json.loads(data)
		self.assertEquals(bar, {'bazes':bazes, 'id':bar['id']})
		
		
	def test_single_link(self):
		Hammock(self.api, resources=(FoosResource,BarsResource,BazesResource), storage=storage, views=(MinimalView(),))
		
		bazes = []
		
		for i in range(0,3):
			result = self.simulate_request('/bazes', 
				                           method='POST', 
				                           headers={
				                           	  'content-type':'application/json',
				                           	  'accept': 'application/json'
				                           }, 
				                           body=json.dumps({'name':'Baz#%d' % i}))
			data = ''.join(result)
			obj = json.loads(data)
			bazes.append(obj)
			
		baz_ids = [x['id'] for x in bazes]
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff': 'things', 'bazes':baz_ids}))
		
		data = ''.join(result)
		foo = json.loads(data)
		
		result = self.simulate_request('/bazes/%s/foo' % baz_ids[0], headers={'accept': 'application/json'})
		self.assertEquals(self.srmock.status, '200 OK')
		data = ''.join(result)
		linked_foo = json.loads(data)
		self.assertEquals(linked_foo, foo)
		