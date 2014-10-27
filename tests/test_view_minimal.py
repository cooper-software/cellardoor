import unittest
import json
import msgpack
from cellardoor.views import MinimalView
from . import create_fake_request


class TestMinimalView(unittest.TestCase):
	
	def test_list_response(self):
		"""
		Should return a simple list for list get methods
		"""
		view = MinimalView()
		objs = [{'foo':123}, {'foo':456}]
		
		req = create_fake_request(headers={'accept':'application/json'})
		content_type, result = view.get_list_response(req, objs)
		self.assertEquals(content_type, 'application/json')
		self.assertEquals(result, json.dumps(objs))
		
		req = create_fake_request(headers={'accept':'application/x-msgpack'})
		content_type, result = view.get_list_response(req, objs)
		self.assertEquals(content_type, 'application/x-msgpack')
		self.assertEquals(result, msgpack.packb(objs))
		
		
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