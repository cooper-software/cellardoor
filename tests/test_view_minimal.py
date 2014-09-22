import unittest
import json
import msgpack
from cellardoor.views import MinimalView
from . import create_fake_request


class TestMinimalView(unittest.TestCase):
	
	def test_collection_response(self):
		"""
		Should return a simple list for collection get methods
		"""
		view = MinimalView()
		objs = [{'foo':123}, {'foo':456}]
		
		req = create_fake_request(headers={'accept':'application/json'})
		content_type, result = view.get_collection_response(req, objs)
		self.assertEquals(content_type, 'application/json')
		self.assertEquals(result, json.dumps({'items':objs}))
		
		req = create_fake_request(headers={'accept':'application/x-msgpack'})
		content_type, result = view.get_collection_response(req, objs)
		self.assertEquals(content_type, 'application/x-msgpack')
		self.assertEquals(result, msgpack.packb({'items':objs}))
		
		
	def test_individual_response(self):
		"""
		Should return a single object for individual get methods
		"""
		view = MinimalView()
		obj = {'foo':123}
		
		req = create_fake_request(headers={'accept':'application/json'})
		content_type, result = view.get_individual_response(req, obj)
		self.assertEquals(content_type, 'application/json')
		self.assertEquals(result, json.dumps(obj))
		
		req = create_fake_request(headers={'accept':'application/x-msgpack'})
		content_type, result = view.get_individual_response(req, obj)
		self.assertEquals(content_type, 'application/x-msgpack')
		self.assertEquals(result, msgpack.packb(obj))