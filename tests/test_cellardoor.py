import unittest
import cellardoor
from mock import Mock

class TestStandardOptionsMixin(unittest.TestCase):
	
	def test_has_options(self):
		options = cellardoor.StandardOptionsMixin()
		self.assertTrue(hasattr(options, '_options'))
		self.assertEquals(options._options, {})
		
		
	def test_identity(self):
		options = cellardoor.StandardOptionsMixin()
		self.assertTrue(hasattr(options, 'identity'))
		self.assertEquals(options.identity(), None)
		result = options.identity('foo')
		self.assertEquals(result, options)
		self.assertEquals(options.identity(), 'foo')
		self.assertEquals(options._options, {'context':{'identity':'foo'}})
		
		
	def test_create_accessor(self):
		options = cellardoor.StandardOptionsMixin('foo', 'bar')
		self.assertTrue(hasattr(options, 'foo'))
		self.assertTrue(hasattr(options, 'bar'))
		result = options.foo(23)
		self.assertEquals(result, options)
		self.assertEquals(options.foo(), 23)
		
		
	def test_merge(self):
		options = cellardoor.StandardOptionsMixin('foo')
		options.foo(1)
		other_options = {'foo':2, 'bar':3}
		merged_options = options._merge_options(other_options)
		self.assertEquals(merged_options, {'foo':1, 'bar':3})
		
		
class TestCellarDoor(unittest.TestCase):
	
	def test_standard_options(self):
		api = cellardoor.CellarDoor()
		self.assertTrue(hasattr(api, 'bypass_authorization'))
		
		
	def test_getattr(self):
		api = cellardoor.CellarDoor()
		api.collections['foo'] = Mock()
		collection_proxy = api.foo
		self.assertIsInstance(collection_proxy, cellardoor.CollectionProxy)
		self.assertEquals(collection_proxy._collection, api.collections['foo'])
		self.assertEquals(collection_proxy._api_options, api._options)
		
	def test_getitem(self):
		api = cellardoor.CellarDoor()
		api.__getattr__ = Mock()
		api['foo']
		api.__getattr__.assert_called_once_with('foo')
		
		
class TestCollectionProxy(unittest.TestCase):
	
	def test_options(self):
		collection = Mock()
		collection_proxy = cellardoor.CollectionProxy(collection)
		self.assertTrue(hasattr(collection_proxy, 'fields'))
		self.assertTrue(hasattr(collection_proxy, 'embed'))
		self.assertTrue(hasattr(collection_proxy, 'bypass_authorization'))
		self.assertTrue(hasattr(collection_proxy, 'show_hidden'))
		
	
	def test_save(self):
		collection = Mock()
		collection.replace = Mock(return_value='replace')
		collection.create = Mock(return_value='create')
		collection_proxy = cellardoor.CollectionProxy(collection)
		collection_proxy.show_hidden(True)
		
		create_result = collection_proxy.save({})
		self.assertEquals(create_result, 'create')
		collection.create.assert_called_once_with({}, show_hidden=True)
		
		replace_result = collection_proxy.save({'_id':'123'})
		self.assertEquals(replace_result, 'replace')
		collection.replace.assert_called_once_with('123', {'_id':'123'}, show_hidden=True)
		
		
	def test_update(self):
		collection = Mock()
		collection.update = Mock(return_value='update')
		collection_proxy = cellardoor.CollectionProxy(collection)
		collection_proxy.show_hidden(True)
		
		result = collection_proxy.update('123', {'foo':'bar'})
		self.assertEquals(result, 'update')
		collection.update.assert_called_once_with('123', {'foo':'bar'}, show_hidden=True)
		
		
	def test_delete(self):
		collection = Mock()
		collection.delete = Mock()
		collection_proxy = cellardoor.CollectionProxy(collection)
		collection_proxy.show_hidden(True)
		
		result = collection_proxy.delete('123')
		self.assertEquals(result, collection_proxy)
		collection.delete.assert_called_once_with('123', show_hidden=True)
		
		
	def test_get(self):
		collection = Mock()
		collection.get = Mock(return_value=1)
		collection_proxy = cellardoor.CollectionProxy(collection)
		collection_proxy.show_hidden(True)
		
		result = collection_proxy.get('123')
		self.assertEquals(result, 1)
		collection.get.assert_called_once_with('123', show_hidden=True)
		
		collection.list = Mock(return_value=[2])
		result = collection_proxy.get({'foo':'bar'})
		self.assertEquals(result, 2)
		collection.list.assert_called_once_with(filter={'foo':'bar'}, limit=1, show_hidden=True)
		
		collection.list = Mock(return_value=[])
		with self.assertRaises(cellardoor.errors.NotFoundError):
			collection_proxy.get({'foo':'bar'})
			
			
	def test_find(self):
		collection = Mock()
		collection_proxy = cellardoor.CollectionProxy(collection)
		result = collection_proxy.find({'foo':'bar'})
		self.assertIsInstance(result, cellardoor.ListProxy)
		self.assertEquals(result._collection, collection)
		self.assertEquals(result._base_options, collection_proxy._options)
		self.assertEquals(result._options['filter'], {'foo':'bar'})
		
		
		
class TestListProxy(unittest.TestCase):
	
	def test_options(self):
		collection = Mock()
		collection_proxy = cellardoor.ListProxy(collection, {}, {})
		self.assertTrue(hasattr(collection_proxy, 'fields'))
		self.assertTrue(hasattr(collection_proxy, 'embed'))
		self.assertTrue(hasattr(collection_proxy, 'sort'))
		self.assertTrue(hasattr(collection_proxy, 'offset'))
		self.assertTrue(hasattr(collection_proxy, 'limit'))
		self.assertTrue(hasattr(collection_proxy, 'bypass_authorization'))
		self.assertTrue(hasattr(collection_proxy, 'show_hidden'))
		
		
	def test_iter(self):
		collection = Mock()
		collection.list = Mock(return_value=[1,2,3])
		collection_proxy = cellardoor.ListProxy(collection, {}, {'foo':'bar'})
		collection_proxy.show_hidden(True)
		result = list(iter(collection_proxy))
		self.assertEquals(result, [1,2,3])
		collection.list.assert_called_once_with(filter={'foo':'bar'}, show_hidden=True)
		
		
	def test_count(self):
		collection = Mock()
		collection.list = Mock(return_value=42)
		collection_proxy = cellardoor.ListProxy(collection, {}, {'foo':'bar'})
		collection_proxy.show_hidden(True)
		result = collection_proxy.count()
		self.assertEquals(result, 42)
		collection.list.assert_called_once_with(filter={'foo':'bar'}, show_hidden=True, count=True)
		
		
	def test_len(self):
		collection_proxy = cellardoor.ListProxy(None, {}, {})
		collection_proxy.count = Mock(return_value=33)
		result = len(collection_proxy)
		self.assertEquals(result, 33)
		collection_proxy.count.assert_called_once()
		
		
	def test_contains(self):
		collection = Mock()
		collection.list = Mock(return_value=[])
		collection_proxy = cellardoor.ListProxy(collection, {}, {'foo':'bar'})
		collection_proxy.show_hidden(True)
		
		result = '123' in collection_proxy
		self.assertEquals(result, False)
		collection.list.assert_called_once_with(filter={'_id':'123', 'foo':'bar'}, limit=1, show_hidden=True)
		
		collection.list = Mock(return_value=[1])
		result = '123' in collection_proxy
		self.assertEquals(result, True)
		
		collection.list = Mock(return_value=[1])
		result = {'_id':'123'} in collection_proxy
		self.assertEquals(result, True)
		collection.list.assert_called_once_with(filter={'_id':'123', 'foo':'bar'}, limit=1, show_hidden=True)
		