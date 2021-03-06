import unittest
import json
from datetime import datetime
from cStringIO import StringIO
from cellardoor.serializers import JSONSerializer


class TestJSONSerializer(unittest.TestCase):
	
	
	def test_simple(self):
		"""
		Should convert simple structures to and from JSON
		"""
		obj = {'foo':'bar'}
		serializer = JSONSerializer()
		json_data = serializer.serialize(obj)
		json.loads(json_data)
		stream = StringIO( json_data )
		unserialized_obj = serializer.unserialize(stream)
		self.assertEquals(unserialized_obj, obj)
		
		
	def test_date_serialization(self):
		"""
		Should convert dates to ISO format when serializing
		"""
		obj = {
			'where': 'My House',
			'when': datetime(2014, 9, 5, 9, 23),
			'another_thing': {
				'foo': 23,
				'bar': [1,2,3]
			}
		}
		serializer = JSONSerializer()
		stream = StringIO( serializer.serialize(obj) )
		unserialized_obj = serializer.unserialize(stream)
		self.assertEquals(unserialized_obj,
			{
				'where': 'My House',
				'when': '2014-09-05T09:23:00',
				'another_thing': {
					'foo': 23,
					'bar': [1,2,3]
				}
			}
		)
		
		
	def test_date_unserialization(self):
		"""
		Should specially formatted date objects to to naive datetimes
		"""
		serializer = JSONSerializer()
		
		stream = StringIO('{ "when": "2014-12-09T21:30:22.272Z" }')
		obj = serializer.unserialize(stream)
		self.assertEquals(
			obj,
			{
				'when': '2014-12-09T21:30:22.272Z'
			}
		)
		
		stream = StringIO('{ "when": { "_date": "2014-12-09T21:30:22.272Z" } }')
		obj = serializer.unserialize(stream)
		self.assertEquals(
			obj,
			{
				'when': datetime(2014, 12, 9, 21, 30, 22, 272)
			}
		)
		
		
	def test_iterables(self):
		"""
		Should serialize any iterable
		"""
		def foo():
			for i in range(0,5):
				yield i
				
		obj = {'foo':foo()}
		serializer = JSONSerializer()
		stream = StringIO( serializer.serialize(obj) )
		unserialized_obj = serializer.unserialize(stream)
		self.assertEquals(unserialized_obj, {'foo': [0,1,2,3,4]})
		
		
	def test_fail(self):
		"""
		Should raise an exception when trying to serialize other things
		"""
		class Foo(object):
			pass
			
		value = {'foo':Foo()}
		serializer = JSONSerializer()
		
		with self.assertRaises(Exception):
			serializer.serialize(obj)