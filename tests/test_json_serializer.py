import unittest
from datetime import datetime
from hammock.serializers import jsonizer


class TestJSONSerializer(unittest.TestCase):
	
	
	def test_simple(self):
		obj = {'foo':'bar'}
		unserialized_obj = jsonizer.unserialize( jsonizer.serialize(obj) )
		self.assertEquals(unserialized_obj, obj)
		
		
	def test_with_date(self):
		obj = {
			'where': 'My House',
			'when': datetime(2014, 9, 5, 9, 23),
			'another_thing': {
				'foo': 23,
				'bar': [1,2,3]
			}
		}
		
		unserialized_obj = jsonizer.unserialize( jsonizer.serialize(obj) )
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