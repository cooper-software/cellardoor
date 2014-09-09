import unittest
import json
from falcon.testing import TestBase
from hammock.model import Model, Entity, One, Many, Text, ListOf
from hammock.resource import Resource
from hammock.methods import ALL
from hammock.storage.mongodb import MongoDBStorage
from hammock.views.minimal import MinimalView
from bson.objectid import ObjectId


class Foo(Entity):
	stuff = Text(required=True)
	optional_stuff = Text()
	bars = Many('Bar')
	
	
class Bar(Entity):
	foo = One(Foo)
	

class FoosResource(Resource):
	entity = Foo
	enabled_methods = ALL
	reference_resources = {
		'bars': 'BarsResource'
	}
	
	
class BarsResource(Resource):
	entity = Bar
	enabled_methods = ALL
	reference_resources = {
		'foo': 'FoosResource'
	}
	

model = Model('hammock_test', (Foo, Bar))
storage = MongoDBStorage()
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
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
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
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
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
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
		self.simulate_request('/foos', method='POST')
		self.assertEquals(self.srmock.status, '415 Unsupported Media Type')
		self.simulate_request('/foos', method='POST', headers={'content-type':'text/plain'})
		self.assertEquals(self.srmock.status, '415 Unsupported Media Type')
		
		
	def test_create_fail_invalid_data(self):
		"""
		Fails if the request fields don't pass validation.
		"""
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
		self.simulate_request('/foos', method='POST', headers={'content-type':'application/json'}, body=json.dumps({}))
		self.assertEquals(self.srmock.status, '400 Bad Request')
		
		
	def test_create_succeed(self):
		"""
		Creates a record in persistent storage if we pass validation.
		"""
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
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
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
		result = self.simulate_request('/foos', 
			                           method='POST', 
			                           headers={
			                           	  'content-type':'application/json',
			                           	  'accept': 'application/json'
			                           }, 
			                           body=json.dumps({'stuff':'foo'}))
		data = ''.join(result)
		obj = json.loads(data)
		result = self.simulate_request('/foos', headers={'accept':'application/json'})
		data = ''.join(result)
		objs = json.loads(data)
		self.assertEquals(objs, {'items':[obj]})
		
		
	def test_patch(self):
		"""
		Can update a subset of fields
		"""
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
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
		data = ''.join(result)
		updated_obj = json.loads(data)
		self.assertEquals(updated_obj, {'id':obj['id'], 'stuff':'baz', 'optional_stuff':'bar'})
		
		
	def test_put(self):
		"""
		Can replace a whole existing item
		"""
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
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
		data = ''.join(result)
		updated_obj = json.loads(data)
		self.assertEquals(updated_obj, {'id':obj['id'], 'stuff':'baz'})
		
		
	def test_delete(self):
		"""
		Can remove an existing item
		"""
		res = FoosResource(storage, (MinimalView(),))
		res.add_to_api(self.api)
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