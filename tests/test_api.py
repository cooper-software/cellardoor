import unittest
from mock import Mock
from cellardoor import errors
from cellardoor.api import API, StandardOptionsMixin, InterfaceProxy, FilterProxy


class TestStandardOptionsMixin(unittest.TestCase):
	
	def test_has_options(self):
		options = StandardOptionsMixin()
		self.assertTrue(hasattr(options, '_options'))
		self.assertEquals(options._options, {})
		
		
	def test_identity(self):
		options = StandardOptionsMixin()
		self.assertTrue(hasattr(options, 'identity'))
		self.assertEquals(options.identity(), None)
		result = options.identity('foo')
		self.assertEquals(result, options)
		self.assertEquals(options.identity(), 'foo')
		self.assertEquals(options._options, {'context':{'identity':'foo'}})
		
		
	def test_create_accessor(self):
		options = StandardOptionsMixin('foo', 'bar')
		self.assertTrue(hasattr(options, 'foo'))
		self.assertTrue(hasattr(options, 'bar'))
		result = options.foo(23)
		self.assertEquals(result, options)
		self.assertEquals(options.foo(), 23)
		
		
	def test_merge(self):
		options = StandardOptionsMixin('foo')
		options.foo(1)
		other_options = {'foo':2, 'bar':3}
		merged_options = options._merge_options(other_options)
		self.assertEquals(merged_options, {'foo':1, 'bar':3})


def get_fake_interface():
	interface = Mock()
	interface.hooks.listeners.keys = Mock(return_value=[])
	return interface
		
		
class TestAPI(unittest.TestCase):
	
	def test_standard_options(self):
		api = API(None)
		self.assertTrue(hasattr(api, 'bypass_authorization'))
		
		
	def test_getattr(self):
		api = API(None)
		api.interfaces['foo'] = get_fake_interface()
		interface_proxy = api.foo
		self.assertIsInstance(interface_proxy, InterfaceProxy)
		self.assertEquals(interface_proxy._interface, api.interfaces['foo'])
		self.assertEquals(interface_proxy._api_options, api._options)
		
	def test_getitem(self):
		api = API(None)
		api.__getattr__ = Mock()
		api['foo']
		api.__getattr__.assert_called_once_with('foo')
		
		
class TestInterfaceProxy(unittest.TestCase):
	
	def test_options(self):
		interface = get_fake_interface()
		interface_proxy = InterfaceProxy(interface)
		self.assertTrue(hasattr(interface_proxy, 'fields'))
		self.assertTrue(hasattr(interface_proxy, 'embed'))
		self.assertTrue(hasattr(interface_proxy, 'bypass_authorization'))
		self.assertTrue(hasattr(interface_proxy, 'show_hidden'))
		
	
	def test_save(self):
		interface = get_fake_interface()
		interface.replace = Mock(return_value='replace')
		interface.create = Mock(return_value='create')
		interface_proxy = InterfaceProxy(interface)
		interface_proxy.show_hidden(True)
		
		create_result = interface_proxy.save({})
		self.assertEquals(create_result, 'create')
		interface.create.assert_called_once_with({}, show_hidden=True)
		
		replace_result = interface_proxy.save({'_id':'123'})
		self.assertEquals(replace_result, 'replace')
		interface.replace.assert_called_once_with('123', {'_id':'123'}, show_hidden=True)
		
		
	def test_update(self):
		interface = get_fake_interface()
		interface.update = Mock(return_value='update')
		interface_proxy = InterfaceProxy(interface)
		interface_proxy.show_hidden(True)
		
		result = interface_proxy.update('123', {'foo':'bar'})
		self.assertEquals(result, 'update')
		interface.update.assert_called_once_with('123', {'foo':'bar'}, show_hidden=True)
		
		
	def test_delete(self):
		interface = get_fake_interface()
		interface.delete = Mock()
		interface_proxy = InterfaceProxy(interface)
		interface_proxy.show_hidden(True)
		
		result = interface_proxy.delete('123')
		self.assertEquals(result, interface_proxy)
		interface.delete.assert_called_once_with('123', show_hidden=True)
		
		
	def test_get(self):
		interface = get_fake_interface()
		interface.get = Mock(return_value=1)
		interface_proxy = InterfaceProxy(interface)
		interface_proxy.show_hidden(True)
		
		result = interface_proxy.get('123')
		self.assertEquals(result, 1)
		interface.get.assert_called_once_with('123', show_hidden=True)
		
		interface.list = Mock(return_value=[2])
		result = interface_proxy.get({'foo':'bar'})
		self.assertEquals(result, 2)
		interface.list.assert_called_once_with(filter={'foo':'bar'}, limit=1, show_hidden=True)
		
		interface.list = Mock(return_value=[])
		with self.assertRaises(errors.NotFoundError):
			interface_proxy.get({'foo':'bar'})
			
			
	def test_find(self):
		interface = get_fake_interface()
		interface_proxy = InterfaceProxy(interface)
		result = interface_proxy.find({'foo':'bar'})
		self.assertIsInstance(result, FilterProxy)
		self.assertEquals(result._interface, interface)
		self.assertEquals(result._base_options, interface_proxy._options)
		self.assertEquals(result._options['filter'], {'foo':'bar'})
		
		
		
class TestFilterProxy(unittest.TestCase):
	
	def test_options(self):
		interface = get_fake_interface()
		interface_proxy = FilterProxy(interface, {}, {})
		self.assertTrue(hasattr(interface_proxy, 'fields'))
		self.assertTrue(hasattr(interface_proxy, 'embed'))
		self.assertTrue(hasattr(interface_proxy, 'sort'))
		self.assertTrue(hasattr(interface_proxy, 'offset'))
		self.assertTrue(hasattr(interface_proxy, 'limit'))
		self.assertTrue(hasattr(interface_proxy, 'bypass_authorization'))
		self.assertTrue(hasattr(interface_proxy, 'show_hidden'))
		
		
	def test_iter(self):
		interface = get_fake_interface()
		interface.list = Mock(return_value=[1,2,3])
		interface_proxy = FilterProxy(interface, {}, {'foo':'bar'})
		interface_proxy.show_hidden(True)
		result = list(iter(interface_proxy))
		self.assertEquals(result, [1,2,3])
		interface.list.assert_called_once_with(filter={'foo':'bar'}, show_hidden=True)
		
		
	def test_count(self):
		interface = get_fake_interface()
		interface.list = Mock(return_value=42)
		interface_proxy = FilterProxy(interface, {}, {'foo':'bar'})
		interface_proxy.show_hidden(True)
		result = interface_proxy.count()
		self.assertEquals(result, 42)
		interface.list.assert_called_once_with(filter={'foo':'bar'}, show_hidden=True, count=True)
		
		
	def test_len(self):
		interface_proxy = FilterProxy(None, {}, {})
		interface_proxy.count = Mock(return_value=33)
		result = len(interface_proxy)
		self.assertEquals(result, 33)
		interface_proxy.count.assert_called_once()
		
		
	def test_contains(self):
		interface = get_fake_interface()
		interface.list = Mock(return_value=[])
		interface_proxy = FilterProxy(interface, {}, {'foo':'bar'})
		interface_proxy.show_hidden(True)
		
		result = '123' in interface_proxy
		self.assertEquals(result, False)
		interface.list.assert_called_once_with(filter={'_id':'123', 'foo':'bar'}, limit=1, show_hidden=True)
		
		interface.list = Mock(return_value=[1])
		result = '123' in interface_proxy
		self.assertEquals(result, True)
		
		interface.list = Mock(return_value=[1])
		result = {'_id':'123'} in interface_proxy
		self.assertEquals(result, True)
		interface.list.assert_called_once_with(filter={'_id':'123', 'foo':'bar'}, limit=1, show_hidden=True)
		