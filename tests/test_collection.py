import unittest
from copy import deepcopy
from mock import Mock
from cellardoor.model import Model, Entity, Reference, Link, Text, ListOf, Integer, Float, Enum
from cellardoor.collection import Collection
from cellardoor.methods import ALL, LIST, GET, CREATE
from cellardoor.storage import Storage
from cellardoor import errors, CellarDoor
from cellardoor.authorization import ObjectProxy

identity = ObjectProxy('identity')
item = ObjectProxy('item')


class CopyingMock(Mock):
	
	def __call__(self, *args, **kwargs):
		args = deepcopy(args)
		kwargs = deepcopy(kwargs)
		return super(CopyingMock, self).__call__(*args, **kwargs)


class Foo(Entity):
	stuff = Text(required=True)
	optional_stuff = Text()
	bars = Link('Bar', 'foo')
	bazes = ListOf(Reference('Baz'))
	embedded_bazes = ListOf(Reference('Baz', embeddable=True))
	embedded_foos = ListOf(Reference('Foo', embeddable=True, embed_by_default=False, embedded_fields=('stuff',)))
	secret = Text(hidden=True)
	
	
class Bar(Entity):
	foo = Reference(Foo)
	embedded_foo = Reference(Foo, embeddable=True)
	bazes = ListOf(Reference('Baz'))
	number = Integer()
	name = Text()
	
	
class Baz(Entity):
	name = Text(required=True)
	foo = Link(Foo, 'bazes', multiple=False)
	embedded_foo = Link(Foo, 'bazes', multiple=False, embeddable=True, embed_by_default=False)
	

class FoosCollection(Collection):
	entity = Foo
	method_authorization = {
		ALL: None
	}
	links = {
		'bars': 'BarsCollection',
		'bazes': 'BazesCollection',
		'embedded_bazes': 'BazesCollection',
		'embedded_foos': 'FoosCollection'
	}
	enabled_filters = ('stuff',)
	enabled_sort = ('stuff',)
	hidden_field_authorization = identity.role == 'admin'
	
	
class ReadOnlyFoosCollection(Collection):
	entity = Foo
	singular_name = 'readonly_foo'
	method_authorization = {
		(LIST, GET): None
	}
	
	
class BarsCollection(Collection):
	entity = Bar
	method_authorization = {
		ALL: None
	}
	links = {
		'foo': FoosCollection,
		'embedded_foo': FoosCollection,
		'bazes': 'BazesCollection'
	}
	enabled_filters = ('number',)
	enabled_sort = ('number', 'name')
	default_sort = ('+name',)
	
	
class BazesCollection(Collection):
	entity = Baz
	plural_name = 'bazes'
	method_authorization = {
		ALL: None
	}
	enabled_filters = ('name',)
	enabled_sort = ('name',)
	links = {
		'foo': FoosCollection,
		'embedded_foo': FoosCollection
	}
	default_limit = 10
	max_limit = 20


class Hidden(Entity):
	name = Text(hidden=True)
	foo = Integer
	
	
class HiddenCollection(Collection):
	entity = Hidden
	enabled_filters = ('name',)
	enabled_sort = ('name',)
	method_authorization = {
		LIST: identity.exists(),
		CREATE: identity.role == 'admin',
		GET: item.foo == 23
	}
	hidden_field_authorization = identity.foo == 'bar'


class Littorina(Entity):
	size = Float()
	
	
class LittorinaLittorea(Littorina):
	shell = Reference('Shell', embeddable=True)
	
	
class Shell(Entity):
	color = Enum('Brown', 'Gray', 'Really brown')
	
	
class LittorinasCollection(Collection):
	entity = Littorina
	method_authorization = {
		ALL: None
	}
	links = {
		'shell': 'ShellsCollection'
	}
	
	
class ShellsCollection(Collection):
	entity = Shell
	method_authorization = {
		ALL: None
	}

storage = None
api = None


class CollectionTest(unittest.TestCase):
	
	def setUp(self):
		global api, storage
		storage = Storage()
		api = CellarDoor(
			collections=(
				FoosCollection, 
				BarsCollection, 
				BazesCollection, 
				HiddenCollection, 
				ReadOnlyFoosCollection,
				LittorinasCollection,
				ShellsCollection
			),
			storage=storage)
		
		
	def test_create_fail_validation(self):
		"""
		Fails if the request fields don't pass validation.
		"""
		with self.assertRaises(errors.CompoundValidationError):
			api.collections['foos'].create({})
	
	
	def test_create_succeed(self):
		"""
		Creates a new item in persistent storage if we pass validation.
		"""
		foo_id = 123
		storage.create = CopyingMock(return_value=foo_id)
		foo = api.collections['foos'].create({'stuff':'foo'})
		storage.create.assert_called_once_with(Foo, {'stuff':'foo'})
		self.assertEquals(foo, {'_id':foo_id, 'stuff':'foo'})
		
		
	def test_list(self):
		"""
		Returns a list of created items
		"""
		saved_foos = []
		
		for i in range(0,3):
			saved_foos.append(
				{'stuff':'foo#%d' % i, '_id':i}
			)
		
		storage.get = CopyingMock(return_value=saved_foos)
		fetched_foos = api.collections['foos'].list()
		storage.get.assert_called_once_with(Foo, sort=(), filter=None, limit=0, offset=0, count=False)
		self.assertEquals(fetched_foos, saved_foos)
		
		
	def test_get(self):
		"""
		Can get a single item
		"""
		foo = {'_id':123, 'stuff':'foo'}
		storage.get_by_id = CopyingMock(return_value=foo)
		fetched_foo = api.collections['foos'].get(foo['_id'])
		storage.get_by_id.assert_called_once_with(Foo, foo['_id'])
		self.assertEquals(fetched_foo, foo)
		
		
	def test_get_nonexistent(self):
		"""
		Trying to fetch a nonexistent item raises an error.
		"""
		storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			api.collections['foos'].get(123)
		
		
	def test_update(self):
		"""
		Can update a subset of fields
		"""
		foo = {'_id':123, 'stuff':'baz'}
		storage.update = Mock(return_value=foo)
		updated_foo = api.collections['foos'].update(123, {'stuff':'baz'})
		storage.update.assert_called_once_with(Foo, 123, {'stuff':'baz'}, replace=False)
		self.assertEquals(updated_foo, foo)
		
		
	def test_update_nonexistent(self):
		"""
		Trying to update a nonexistent item raises an error.
		"""
		storage.update = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			api.collections['foos'].update(123, {})
		
		
	def test_replace(self):
		"""
		Can replace a whole existing item
		"""
		foo = {'_id':123, 'stuff':'baz'}
		storage.update = Mock(return_value=foo)
		updated_foo = api.collections['foos'].replace(123, {'stuff':'baz'})
		storage.update.assert_called_once_with(Foo, 123, {'stuff':'baz'}, replace=True)
		self.assertEquals(updated_foo, foo)
		
		
	def test_replace_nonexistent(self):
		"""
		Trying to replace a nonexistent item raises an error.
		"""
		storage.update = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			api.collections['foos'].replace(123, {'stuff':'foo'})
		
		
	def test_delete_nonexistent(self):
		"""
		Raise an error when trying to delete an item that doesn't exist
		"""
		storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			api.collections['foos'].delete(123)
		
		
	def test_delete(self):
		"""
		Can remove an existing item
		"""
		storage.get_by_id = Mock({'_id':123, 'stuff':'foo'})
		storage.delete = Mock(return_value=None)
		api.collections['foos'].delete(123)
		storage.get_by_id.assert_called_once_with(Foo, 123)
		storage.delete.assert_called_once_with(Foo, 123)
		
		
	def test_single_reference_validation_fail(self):
		"""
		Fails validation if setting a reference to a non-existent ID.
		"""
		storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.CompoundValidationError):
			bar = api.collections['bars'].create({'foo':'123'})
		
		
	def test_single_reference(self):
		"""
		Can get a reference through a link.
		"""
		foo = {'_id':'123', 'stuff':'foo'}
		bar = {'_id':'321', 'foo':'123'}
		
		api.collections['foos'].storage = Storage()
		api.collections['bars'].storage = Storage()
		api.collections['foos'].storage.get_by_id = Mock(return_value=foo)
		api.collections['bars'].storage.get_by_id = Mock(return_value=bar)
		
		linked_foo = api.collections['bars'].link('321', 'foo')
		self.assertEquals(linked_foo, foo)
		api.collections['bars'].storage.get_by_id.assert_called_once_with(Bar, '321')
		api.collections['foos'].storage.get_by_id.assert_called_once_with(Foo, '123')
		
		
	def test_single_reference_get_embedded(self):
		"""
		Embedded references are included when fetching the referencing item.
		"""
		
		foo = {'_id':'123', 'stuff':'foo'}
		bar = {'_id':'321', 'embedded_foo':'123'}
		
		api.collections['foos'].storage = Storage()
		api.collections['bars'].storage = Storage()
		api.collections['foos'].storage.get_by_id = Mock(return_value=foo)
		api.collections['bars'].storage.get_by_id = Mock(return_value=bar)
		
		bar = api.collections['bars'].get('321')
		self.assertEquals(bar['embedded_foo'], foo)
		
		
	def test_multiple_reference(self):
		"""
		Can set a list of references when creating an item
		"""
		created_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			created_bazes.append(baz)
			baz_ids.append(baz['_id'])
			
		foo = {'_id':'123', 'bazes':baz_ids}
		
		api.collections['foos'].set_storage(Storage())
		api.collections['bazes'].set_storage(Storage())
		api.collections['foos'].storage.get_by_id = Mock(return_value=foo)
		api.collections['foos'].storage.check_filter = Mock(return_value=None)
		api.collections['bazes'].storage.get_by_ids = Mock(return_value=created_bazes)
		api.collections['bazes'].storage.check_filter = Mock(return_value=None)
		
		linked_bazes = api.collections['foos'].link(foo['_id'], 'bazes', sort=('+name',), filter={'name':'foo'}, offset=10, limit=20)
		self.assertEquals(linked_bazes, created_bazes)
		api.collections['bazes'].storage.get_by_ids.assert_called_once_with(Baz, baz_ids, sort=('+name',), filter={'name':'foo'}, offset=10, limit=20, count=False)
		
		
	def test_multiple_reference_get_embedded(self):
		"""
		Embedded reference list is included when fetching the referencing item.
		"""
		created_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			created_bazes.append(baz)
			baz_ids.append(baz['_id'])
			
		foo = {'_id':'123', 'embedded_bazes':baz_ids}
		
		api.collections['foos'].storage = Storage()
		api.collections['bazes'].storage = Storage()
		api.collections['foos'].storage.get_by_id = Mock(return_value=foo)
		api.collections['bazes'].storage.get_by_ids = Mock(return_value=created_bazes)
		
		fetched_foo = api.collections['foos'].get(foo['_id'])
		self.assertEquals(fetched_foo['embedded_bazes'], created_bazes)
		
		
	def test_single_link(self):
		"""
		Can resolve a single link.
		"""
		created_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			created_bazes.append(baz)
			baz_ids.append(baz['_id'])
			
		foo = {'_id':'123', 'bazes':baz_ids}
		
		api.collections['foos'].storage = Storage()
		api.collections['bazes'].storage = Storage()
		api.collections['foos'].storage.get = Mock(return_value=[foo])
		api.collections['bazes'].storage.get_by_id = Mock(return_value=created_bazes[0])
		
		linked_foo = api.collections['bazes'].link(baz_ids[0], 'foo')
		api.collections['bazes'].storage.get_by_id.assert_called_once_with(Baz, baz_ids[0])
		api.collections['foos'].storage.get.assert_called_once_with(Foo, filter={'bazes':baz_ids[0]}, limit=1)
		self.assertEquals(linked_foo, foo)
		
		
	def test_single_link_embedded(self):
		"""
		Single embedded links are automatically resolved.
		"""
		created_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			created_bazes.append(baz)
			baz_ids.append(baz['_id'])
			
		foo = {'_id':'123', 'bazes':baz_ids}
		
		api.collections['foos'].storage = Storage()
		api.collections['bazes'].storage = Storage()
		api.collections['foos'].storage.get = Mock(return_value=[foo])
		api.collections['bazes'].storage.get_by_id = Mock(return_value=created_bazes[0])
		
		baz = api.collections['bazes'].get(baz_ids[0], embed=('embedded_foo',))
		self.assertEquals(baz['embedded_foo'], foo)
		
		
	def test_multiple_link(self):
		"""
		Can resolve a multiple link the same way as a reference.
		"""
		foo = {'stuff':'foo', '_id':'123'}
		
		bars = []
		bar_ids = []
		for i in range(0,3):
			bar = {'foo':foo['_id'], '_id':'%s' % i}
			bars.append(bar)
			bar_ids.append(bar['_id'])
		
		api.collections['foos'].set_storage(Storage())
		api.collections['bars'].set_storage(Storage())
		api.collections['foos'].storage.get_by_id = Mock(return_value=foo)
		api.collections['bars'].storage.get = Mock(return_value=bars)
		api.collections['bars'].storage.check_filter = Mock(return_value=None)
		
		linked_bars = api.collections['foos'].link(foo['_id'], 'bars', sort=('-name',), filter={'number':'7'}, limit=10, offset=20)
		api.collections['foos'].storage.get_by_id.assert_called_once_with(Foo, foo['_id'])
		api.collections['bars'].storage.get.assert_called_once_with(Bar, sort=('-name',), filter={'foo': '123', 'number':'7'}, limit=10, offset=20, count=False)
		self.assertEquals(linked_bars, bars)
		
		
	def test_embed_polymorphic(self):
		"""Collections properly embed references when fetching descendants of the collection's entity"""
		api.collections['littorinas'].set_storage(Storage())
		api.collections['littorinas'].storage.get = Mock(return_value=[
			{'_id': '1', '_type':'Littorina.LittorinaLittorea', 'shell':'2'}])
		
		api.collections['shells'].set_storage(Storage())
		api.collections['shells'].storage.get_by_id = Mock(return_value={'_id':'2', 'color': 'Really brown'})
		
		result = api.collections['littorinas'].list()
		api.collections['shells'].storage.get_by_id.assert_called_once_with(Shell, '2')
		self.assertEquals(result, [{'_id': '1', '_type':'Littorina.LittorinaLittorea', 'shell':{'_id':'2', 'color': 'Really brown'}}])
		
		
	def test_sort_fail(self):
		"""
		Trying to sort by a sort-disabled field raises an error.
		"""
		with self.assertRaises(errors.DisabledFieldError) as cm:
			api.collections['foos'].list(sort=('+optional_stuff',))
		
		
	def test_sort_default(self):
		"""
		If no sort is set, the default is used.
		"""
		storage.get = Mock(return_value=[])
		api.collections['bars'].list()
		storage.get.assert_called_once_with(Bar, sort=('+name',), filter=None, limit=0, offset=0, count=False)
		
		
	def test_auth_required_not_present(self):
		"""Raise NotAuthenticatedError if authorization requires authentication and it is not present."""
		with self.assertRaises(errors.NotAuthenticatedError):
			api.collections['hiddens'].list()
			
			
	def test_auth_required_present(self):
		"""Don't raise NotAuthenticatedError if authentication is required and present."""
		storage.get = Mock(return_value=[])
		api.collections['hiddens'].list(context={'identity':{'foo':'bar'}})
		
		
	def test_auth_failed(self):
		"""Raises NotAuthorizedError if the authorization rule fails"""
		with self.assertRaises(errors.NotAuthorizedError):
			api.collections['hiddens'].create({}, context={'identity':{}})
			
		with self.assertRaises(errors.NotAuthorizedError):
			api.collections['hiddens'].create({}, context={'identity':{'role':'foo'}})
			
			
	def test_auth_pass(self):
		"""Does not raise NotAuthorizedError if the authorization rule passes"""
		storage.create = Mock(return_value={})
		api.collections['hiddens'].create({}, context={'identity':{'role':'admin'}})
		
		
	def test_auth_result_fail(self):
		"""Raises NotAuthorizedError if a result rule doesn't pass."""
		api.collections['hiddens'].storage.get_by_id = Mock(return_value={'foo':700})
		with self.assertRaises(errors.NotAuthorizedError):
			api.collections['hiddens'].get(123)
		
		
	def test_auth_result_pass(self):
		"""Does not raise NotAuthorizedError if a result rule passes."""
		api.collections['hiddens'].storage.get_by_id = Mock(return_value={'foo':23})
		api.collections['hiddens'].get(123)
		
		
	def test_hidden_result(self):
		"""Hidden fields aren't shown in results."""
		storage.create = Mock(return_value={'_id':'123', 'name':'foo'})
		obj = api.collections['hiddens'].create({'name':'foo'}, context={'identity':{'role':'admin'}})
		self.assertNotIn('name', obj)
		
		
	def test_hidden_show_fail(self):
		"""Hidden fields aren't shown in results even when show_hidden=True if the user is not authorized."""
		storage.get_by_id = Mock(return_value={'_id':'123', 'name':'foo', 'foo':23})
		obj = api.collections['hiddens'].get('123', show_hidden=True)
		self.assertNotIn('name', obj)
		
		
	def test_hidden_succeed(self):
		"""Hidden fields are shown when show_hidden=True and the user is authorized."""
		storage.get_by_id = Mock(return_value={'_id':'123', 'name':'foo', 'foo':23})
		obj = api.collections['hiddens'].get('123', show_hidden=True, context={'identity':{'foo':'bar'}})
		self.assertIn('name', obj)
		
		
	def test_hidden_filter(self):
		"""Can't filter by a hidden field without authorization."""
		storage.check_filter = Mock(side_effect=errors.DisabledFieldError)
		with self.assertRaises(errors.DisabledFieldError):
			api.collections['hiddens'].list(filter={'name':'zoomy'}, context={'identity':{}})
		storage.check_filter.assert_called_once_with({'name':'zoomy'}, set(['_type', '_id']), {'identity': {}})
		
		
	def test_hidden_filter_authorized(self):
		"""Can filter by a hidden field when authorized."""
		storage.check_filter = Mock(return_value=None)
		storage.get = Mock(return_value=[])
		api.collections['hiddens'].list(filter={'name':'zoomy'}, context={'identity':{'foo':'bar'}})
		storage.check_filter.assert_called_once_with({'name':'zoomy'}, set(['name', '_type', '_id']),  {'item': [], 'identity': {'foo': 'bar'}})
		
		
	def test_hidden_sort_fail(self):
		"""Can't sort by a hidden field without authorization."""
		with self.assertRaises(errors.DisabledFieldError) as cm:
			api.collections['hiddens'].list(sort=('+name',), context={'identity':{}})
		self.assertEquals(cm.exception.message, 'The "name" field cannot be used for sorting.')
		
		
	def test_authorization_bypass(self):
		"""Can bypass authorization for methods, filters and sort."""
		storage.get = Mock(return_value=[{'name':'zoomy', 'foo':23}])
		results = api.collections['hiddens'].list(filter={'name':'zoomy'}, sort=('+name',), bypass_authorization=True, show_hidden=True)
		storage.get.assert_called_once_with(Hidden, sort=('+name',), filter={'name':'zoomy'}, limit=0, offset=0, count=False)
		self.assertEquals(results, [{'name':'zoomy', 'foo':23}])
		
		
	def test_entity_hooks(self):
		"""Collections call entity create, update and delete hooks"""
		pre_create = CopyingMock()
		post_create = CopyingMock()
		pre_update = CopyingMock()
		post_update = CopyingMock()
		pre_delete = CopyingMock()
		post_delete = CopyingMock()
		hooks = api.collections['foos'].entity.hooks
		hooks.pre('create', pre_create)
		hooks.post('create', post_create)
		hooks.pre('update', pre_update)
		hooks.post('update', post_update)
		hooks.pre('delete', pre_delete)
		hooks.post('delete', post_delete)
		
		context = {'foo':23}
		
		storage.create = Mock(return_value='123')
		storage.update = Mock(return_value={'_id':'123', 'stuff':'nothings'})
		storage.delete = Mock(return_value=None)
		storage.get_by_id = Mock(return_value={'_id':'123', 'stuff':'nothings'})
		
		foo = api.collections['foos'].create({'stuff':'things'}, context=context.copy())
		create_context = context.copy()
		create_context['item'] = foo
		pre_create.assert_called_once_with({'stuff':'things'}, context)
		post_create.assert_called_once_with(foo, create_context)
		
		foo = api.collections['foos'].update(foo['_id'], {'stuff':'nothings'}, context=context.copy())
		update_context = context.copy()
		update_context['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'nothings'}, context)
		post_update.assert_called_with(foo, update_context)
		
		foo = api.collections['foos'].replace(foo['_id'], {'stuff':'somethings'}, context=context.copy())
		replace_context = context.copy()
		replace_context['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'somethings'}, context)
		post_update.assert_called_with(foo, replace_context)
		
		api.collections['foos'].delete(foo['_id'], context=context.copy())
		delete_context = context.copy()
		delete_context['item'] = foo
		pre_delete.assert_called_once_with(foo['_id'], context)
		post_delete.assert_called_once_with(foo['_id'], delete_context)
		
		
	def test_collection_hooks(self):
		"""Collections have create, update and delete hooks"""
		pre_create = CopyingMock()
		post_create = CopyingMock()
		pre_update = CopyingMock()
		post_update = CopyingMock()
		pre_delete = CopyingMock()
		post_delete = CopyingMock()
		hooks = api.collections['foos'].hooks
		hooks.pre('create', pre_create)
		hooks.post('create', post_create)
		hooks.pre('update', pre_update)
		hooks.post('update', post_update)
		hooks.pre('delete', pre_delete)
		hooks.post('delete', post_delete)
		
		context = {'foo':23}
		
		storage.create = Mock(return_value='123')
		storage.update = Mock(return_value={'_id':'123', 'stuff':'nothings'})
		storage.delete = Mock(return_value=None)
		storage.get_by_id = Mock(return_value={'_id':'123', 'stuff':'nothings'})
		
		foo = api.collections['foos'].create({'stuff':'things'}, context=context.copy())
		create_context = context.copy()
		create_context['item'] = foo
		pre_create.assert_called_once_with({'stuff':'things'}, context)
		post_create.assert_called_once_with(foo, create_context)
		
		foo = api.collections['foos'].update(foo['_id'], {'stuff':'nothings'}, context=context.copy())
		update_context = context.copy()
		update_context['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'nothings'}, context)
		post_update.assert_called_with(foo, update_context)
		
		foo = api.collections['foos'].replace(foo['_id'], {'stuff':'somethings'}, context=context.copy())
		replace_context = context.copy()
		replace_context['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'somethings'}, context)
		post_update.assert_called_with(foo, replace_context)
		
		api.collections['foos'].delete(foo['_id'], context=context.copy())
		delete_context = context.copy()
		delete_context['item'] = foo
		pre_delete.assert_called_once_with(foo['_id'], context)
		post_delete.assert_called_once_with(foo['_id'], delete_context)
		
		
	def test_disabled_method(self):
		"""An error is raised when attempting to call a disabled method."""
		with self.assertRaises(errors.DisabledMethodError):
			api.collections['readonly_foos'].create({})
		
		
	def test_passes_version(self):
		"""When updating, the _version field is passed through to the storage method"""
		storage.update = Mock(return_value={'_id':'123'})
		storage.get_by_id = Mock(return_value={'_id':'123'})
		api.collections['foos'].update('123', {'_version':57})
		storage.update.assert_called_with(Foo, '123', {'_version':57}, replace=False)
		api.collections['foos'].replace('123', {'stuff':'things', '_version':57})
		storage.update.assert_called_with(Foo, '123', {'stuff':'things', '_version':57}, replace=True)
		
		
	def test_default_limit(self):
		"""A default limit is used when limit is not passed"""
		storage.get = Mock(return_value=[])
		api.collections['bazes'].list()
		storage.get.assert_called_once_with(Baz, sort=(), filter=None, offset=0, limit=10, count=False)
		
		
	def test_max_limit(self):
		"""Limit can't exceed max_limit"""
		storage.get = Mock(return_value=[])
		api.collections['bazes'].list(limit=50)
		storage.get.assert_called_once_with(Baz, sort=(), filter=None, offset=0, limit=20, count=False)
		
		
	def test_default_embedded_not_default(self):
		"""A reference can be embeddable but not embedded"""
		storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		storage.get_by_ids = Mock(return_value=[])
		api.collections['foos'].list()
		self.assertFalse(storage.get_by_ids.called)
		
		
	def test_default_not_embedded_not_default_included(self):
		"""A reference that is not embedded by default can still be embedded"""
		storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		storage.get_by_ids = Mock(return_value=[])
		api.collections['foos'].list(embed=['embedded_foos'])
		storage.get_by_ids.assert_called_once_with(Foo, ['1','2','3'], sort=(), filter=None, limit=0, offset=0, count=False)
		
		
	def test_embeddable_included_if_fields_set(self):
		"""An embeddable field is included if it is in the fields argument"""
		storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		storage.get_by_ids = Mock(return_value=[])
		api.collections['foos'].list(fields=['embedded_foos'])
		storage.get_by_ids.assert_called_once_with(Foo, ['1','2','3'], sort=(), filter=None, limit=0, offset=0, count=False)
		
		
	def test_embeddable_fields(self):
		"""Only fields in an entity's embedded_fields list are included"""
		storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		storage.get_by_ids = Mock(return_value=[{'_id':'666', 'stuff':123, 'optional_stuff':456}])
		result = api.collections['foos'].list(embed=('embedded_foos',))
		self.assertEquals(result, [{'_id':'123', 'embedded_foos':[{'_id':'666', 'stuff':123}]}])
		
		
	def test_field_subset(self):
		"""Can fetch only a subset of fields"""
		storage.get_by_id = CopyingMock(return_value={'_id':'123', 'stuff':123, 'optional_stuff':456})
		result = api.collections['foos'].get('123', fields=('optional_stuff',))
		self.assertEquals(result, {'_id':'123', 'optional_stuff':456})
		
		
	def test_no_fields(self):
		"""Only an item's ID is included if fields is an empty list"""
		storage.get_by_id = CopyingMock(return_value={'_id':'123', 'stuff':123, 'optional_stuff':456})
		result = api.collections['foos'].get('123', fields=())
		self.assertEquals(result, {'_id':'123'})
		
		
	def test_fields_empty(self):
		"""All of an item's visible fields are returned if the fields list is omitted"""
		foo = {'_id':'123', 'stuff':123, 'optional_stuff':456}
		storage.get_by_id = CopyingMock(return_value=foo)
		result = api.collections['foos'].get('123')
		self.assertEquals(result, foo)
		
		
	def test_fields_empty_hidden_field(self):
		"""All of an item's visible fields are returned if the fields list is omitted when an entity has hidden fields"""
		storage.get_by_id = CopyingMock(return_value={'_id':'123', 'name':'hidden', 'foo':23})
		result = api.collections['hiddens'].get('123')
		self.assertEquals(result, {'_id':'123', 'foo':23})
		
		
	def test_fields_empty_hidden_list(self):
		"""All of an item's visible fields are returned when listing items"""
		storage.get = CopyingMock(return_value=[{'_id':'123', 'stuff':'foo', 'secret':'i like valuer'}])
		result = api.collections['foos'].list()
		self.assertEquals(result, [{'_id':'123', 'stuff':'foo'}])
		
		
	def test_count(self):
		"""Can get a count instead of a list of items"""
		storage.get = Mock(return_value=42)
		result = api.collections['foos'].list(count=True)
		self.assertEquals(result, 42)
		storage.get.assert_called_once_with(Foo, filter=None, sort=(), offset=0, limit=0, count=True)
		
		
	def test_count_reference(self):
		"""Can count a list reference instead of getting the items"""
		storage.get_by_id = Mock(return_value={'_id':'123', 'bazes':['1','2','3']})
		storage.get_by_ids = Mock(return_value=42)
		result = api.collections['foos'].link('123', 'bazes', count=True)
		self.assertEquals(result, 42)
		storage.get_by_ids.assert_called_with(Baz, ['1','2','3'], filter=None, sort=(), offset=0, limit=10, count=True)
		
		
	def test_count_link(self):
		"""Can count a multiple link instead of getting the items"""
		foo = {'stuff':'foo', '_id':'123'}
		
		bars = []
		for i in range(0,3):
			bar = {'foo':foo['_id'], '_id':'%s' % i}
			bars.append(bar)
		
		api.collections['foos'].set_storage(Storage())
		api.collections['bars'].set_storage(Storage())
		api.collections['foos'].storage.get_by_id = Mock(return_value=foo)
		api.collections['bars'].storage.get = Mock(return_value=3)
		api.collections['bars'].storage.check_filter = Mock(return_value=None)
		
		result = api.collections['foos'].link(foo['_id'], 'bars', count=True)
		self.assertEquals(result, 3)
		api.collections['bars'].storage.get.assert_called_once_with(Bar, filter={'foo':'123'}, sort=('+name',), offset=0, limit=0, count=True)
		