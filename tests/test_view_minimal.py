import unittest
import json
import msgpack
from cellardoor.views import MinimalView


class TestMinimalView(unittest.TestCase):
	
	def test_list_response(self):
		"""
		Should return a simple list for list get methods
		"""
		view = MinimalView()
		objs = [{'foo':123}, {'foo':456}]
		
		content_type, result = view.get_list_response('application/json', objs)
		self.assertEquals(content_type, 'application/json')
		self.assertEquals(result, json.dumps(objs))
		
		content_type, result = view.get_list_response('application/x-msgpack', objs)
		self.assertEquals(content_type, 'application/x-msgpack')
		self.assertEquals(result, msgpack.packb(objs))
		
		
	def test_individual_response(self):
		"""
		Should return a single object for individual get methods
		"""
		view = MinimalView()
		obj = {'foo':123}
		
		content_type, result = view.get_individual_response('application/json', obj)
		self.assertEquals(content_type, 'application/json')
		self.assertEquals(result, json.dumps(obj))
		
		content_type, result = view.get_individual_response('application/x-msgpack', obj)
		self.assertEquals(content_type, 'application/x-msgpack')
		self.assertEquals(result, msgpack.packb(obj))