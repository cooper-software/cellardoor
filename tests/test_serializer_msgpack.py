import unittest
import msgpack
from datetime import datetime
from cStringIO import StringIO
from hammock.serializers import MsgPackSerializer


class TestJSONSerializer(unittest.TestCase):
	
	
	def test_simple(self):
		"""
		Should convert simple structures to and from JSON
		"""
		obj = {'foo':'bar'}
		serializer = MsgPackSerializer()
		packed_data = serializer.serialize(obj)
		msgpack.unpackb(packed_data)
		stream = StringIO( packed_data )
		unserialized_obj = serializer.unserialize(stream)
		self.assertEquals(unserialized_obj, obj)
		
		
	def test_with_date(self):
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
		serializer = MsgPackSerializer()
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
		
		
	def test_iterables(self):
		"""
		Should serialize any iterable
		"""
		def foo():
			for i in range(0,5):
				yield i
				
		obj = {'foo':foo()}
		serializer = MsgPackSerializer()
		stream = StringIO( serializer.serialize(obj) )
		unserialized_obj = serializer.unserialize(stream)
		self.assertEquals(unserialized_obj, {'foo': [0,1,2,3,4]})
		