import unittest
from cellardoor.storage import Storage


class TestStorage(unittest.TestCase):
	
	def test_abstract_storage(self):
		storage = Storage()
		
		with self.assertRaises(NotImplementedError):
			storage.get(None)
			
		with self.assertRaises(NotImplementedError):
			storage.get_by_ids(None, None)
			
		with self.assertRaises(NotImplementedError):
			storage.get_by_id(None, None)
			
		with self.assertRaises(NotImplementedError):
			storage.create(None, None)
			
		with self.assertRaises(NotImplementedError):
			storage.update(None, None, None)
			
		with self.assertRaises(NotImplementedError):
			storage.delete(None, None)
			
		with self.assertRaises(NotImplementedError):
			storage.check_filter(None, None)