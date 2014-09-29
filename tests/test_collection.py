import unittest
from copy import deepcopy
from mock import Mock
from cellardoor.model import Model, Entity, Reference, Link, Text, ListOf, TypeOf
from cellardoor.collection import Collection
from cellardoor.methods import ALL, LIST, GET, CREATE
from cellardoor.storage import Storage
from cellardoor import errors, CellarDoor
from cellardoor import authorization as auth


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
	number = TypeOf(int)
	name = Text()
	
	
class Baz(Entity):
	name = Text(required=True)
	foo = Link(Foo, 'bazes', multiple=False)
	embedded_foo = Link(Foo, 'bazes', multiple=False, embeddable=True, embed_by_default=False)
	
	
class Hidden(Entity):
	name = Text(hidden=True)
	foo = TypeOf(int)
	

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
	hidden_field_authorization = auth.identity.role == 'admin'
	
	
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
	
	
class HiddenCollection(Collection):
	entity = Hidden
	enabled_filters = ('name',)
	enabled_sort = ('name',)
	method_authorization = {
		LIST: auth.identity.exists(),
		CREATE: auth.identity.role == 'admin',
		GET: auth.item.foo == 23
	}
	hidden_field_authorization = auth.identity.foo == 'bar'
	
	
class ReadOnlyFoosCollection(Collection):
	entity = Foo
	singular_name = 'readonly_foo'
	method_authorization = {
		LIST: None,
		GET: None
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
				ReadOnlyFoosCollection
			),
			storage=storage)
		
		
	def test_create_fail_validation(self):
		"""
		Fails if the request fields don't pass validation.
		"""
		with self.assertRaises(errors.CompoundValidationError):
			api.foos.create({})
	
	
	def test_create_succeed(self):
		"""
		Creates a new item in persistent storage if we pass validation.
		"""
		foo_id = 123
		storage.create = CopyingMock(return_value=foo_id)
		foo = api.foos.create({'stuff':'foo'})
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
		fetched_foos = api.foos.list()
		storage.get.assert_called_once_with(Foo, sort=(), filter=None, limit=0, offset=0)
		self.assertEquals(fetched_foos, saved_foos)
		
		
	def test_get(self):
		"""
		Can get a single item
		"""
		foo = {'_id':123, 'stuff':'foo'}
		storage.get_by_id = CopyingMock(return_value=foo)
		fetched_foo = api.foos.get(foo['_id'])
		storage.get_by_id.assert_called_once_with(Foo, foo['_id'])
		self.assertEquals(fetched_foo, foo)
		
		
	def test_get_nonexistent(self):
		"""
		Trying to fetch a nonexistent item raises an error.
		"""
		storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			api.foos.get(123)
		
		
	def test_update(self):
		"""
		Can update a subset of fields
		"""
		foo = {'_id':123, 'stuff':'baz'}
		storage.update = Mock(return_value=foo)
		updated_foo = api.foos.update(123, {'stuff':'baz'})
		storage.update.assert_called_once_with(Foo, 123, {'stuff':'baz'}, replace=False)
		self.assertEquals(updated_foo, foo)
		
		
	def test_update_nonexistent(self):
		"""
		Trying to update a nonexistent item raises an error.
		"""
		storage.update = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			api.foos.update(123, {})
		
		
	def test_replace(self):
		"""
		Can replace a whole existing item
		"""
		foo = {'_id':123, 'stuff':'baz'}
		storage.update = Mock(return_value=foo)
		updated_foo = api.foos.replace(123, {'stuff':'baz'})
		storage.update.assert_called_once_with(Foo, 123, {'stuff':'baz'}, replace=True)
		self.assertEquals(updated_foo, foo)
		
		
	def test_replace_nonexistent(self):
		"""
		Trying to replace a nonexistent item raises an error.
		"""
		storage.update = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			api.foos.replace(123, {'stuff':'foo'})
		
		
	def test_delete_nonexistent(self):
		"""
		Raise an error when trying to delete an item that doesn't exist
		"""
		storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			api.foos.delete(123)
		
		
	def test_delete(self):
		"""
		Can remove an existing item
		"""
		storage.get_by_id = Mock({'_id':123, 'stuff':'foo'})
		storage.delete = Mock(return_value=None)
		api.foos.delete(123)
		storage.get_by_id.assert_called_once_with(Foo, 123)
		storage.delete.assert_called_once_with(Foo, 123)
		
		
	def test_single_reference_validation_fail(self):
		"""
		Fails validation if setting a reference to a non-existent ID.
		"""
		storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.CompoundValidationError):
			bar = api.bars.create({'foo':'123'})
		
		
	def test_single_reference(self):
		"""
		Can get a reference through a link.
		"""
		foo = {'_id':'123', 'stuff':'foo'}
		bar = {'_id':'321', 'foo':'123'}
		
		api.foos.storage = Storage()
		api.bars.storage = Storage()
		api.foos.storage.get_by_id = Mock(return_value=foo)
		api.bars.storage.get_by_id = Mock(return_value=bar)
		
		linked_foo = api.bars.link('321', 'foo')
		self.assertEquals(linked_foo, foo)
		api.bars.storage.get_by_id.assert_called_once_with(Bar, '321')
		api.foos.storage.get_by_id.assert_called_once_with(Foo, '123')
		
		
	def test_single_reference_get_embedded(self):
		"""
		Embedded references are included when fetching the referencing item.
		"""
		
		foo = {'_id':'123', 'stuff':'foo'}
		bar = {'_id':'321', 'embedded_foo':'123'}
		
		api.foos.storage = Storage()
		api.bars.storage = Storage()
		api.foos.storage.get_by_id = Mock(return_value=foo)
		api.bars.storage.get_by_id = Mock(return_value=bar)
		
		bar = api.bars.get('321')
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
		
		api.foos.set_storage(Storage())
		api.bazes.set_storage(Storage())
		api.foos.storage.get_by_id = Mock(return_value=foo)
		api.foos.storage.check_filter = Mock(return_value=None)
		api.bazes.storage.get_by_ids = Mock(return_value=created_bazes)
		api.bazes.storage.check_filter = Mock(return_value=None)
		
		linked_bazes = api.foos.link(foo['_id'], 'bazes', sort=('+name',), filter={'name':'foo'}, offset=10, limit=20)
		self.assertEquals(linked_bazes, created_bazes)
		api.bazes.storage.get_by_ids.assert_called_once_with(Baz, baz_ids, sort=('+name',), filter={'name':'foo'}, offset=10, limit=20)
		
		
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
		
		api.foos.storage = Storage()
		api.bazes.storage = Storage()
		api.foos.storage.get_by_id = Mock(return_value=foo)
		api.bazes.storage.get_by_ids = Mock(return_value=created_bazes)
		
		fetched_foo = api.foos.get(foo['_id'])
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
		
		api.foos.storage = Storage()
		api.bazes.storage = Storage()
		api.foos.storage.get = Mock(return_value=[foo])
		api.bazes.storage.get_by_id = Mock(return_value=created_bazes[0])
		
		linked_foo = api.bazes.link(baz_ids[0], 'foo')
		api.bazes.storage.get_by_id.assert_called_once_with(Baz, baz_ids[0])
		api.foos.storage.get.assert_called_once_with(Foo, filter={'bazes':baz_ids[0]}, limit=1)
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
		
		api.foos.storage = Storage()
		api.bazes.storage = Storage()
		api.foos.storage.get = Mock(return_value=[foo])
		api.bazes.storage.get_by_id = Mock(return_value=created_bazes[0])
		
		baz = api.bazes.get(baz_ids[0], embed=('embedded_foo',))
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
		
		api.foos.set_storage(Storage())
		api.bars.set_storage(Storage())
		api.foos.storage.get_by_id = Mock(return_value=foo)
		api.bars.storage.get = Mock(return_value=bars)
		api.bars.storage.check_filter = Mock(return_value=None)
		
		linked_bars = api.foos.link(foo['_id'], 'bars', sort=('-name',), filter={'number':'7'}, limit=10, offset=20)
		api.foos.storage.get_by_id.assert_called_once_with(Foo, foo['_id'])
		api.bars.storage.get.assert_called_once_with(Bar, sort=('-name',), filter={'foo': '123', 'number':'7'}, limit=10, offset=20)
		self.assertEquals(linked_bars, bars)
		
		
	def test_sort_fail(self):
		"""
		Trying to sort by a sort-disabled field raises an error.
		"""
		with self.assertRaises(errors.DisabledFieldError) as cm:
			api.foos.list(sort=('+optional_stuff',))
		
		
	def test_sort_default(self):
		"""
		If no sort is set, the default is used.
		"""
		storage.get = Mock(return_value=[])
		api.bars.list()
		storage.get.assert_called_once_with(Bar, sort=('+name',), filter=None, limit=0, offset=0)
		
		
	def test_auth_required_not_present(self):
		"""Raise NotAuthenticatedError if authorization requires authentication and it is not present."""
		with self.assertRaises(errors.NotAuthenticatedError):
			api.hiddens.list()
			
			
	def test_auth_required_present(self):
		"""Don't raise NotAuthenticatedError if authentication is required and present."""
		storage.get = Mock(return_value=[])
		api.hiddens.list(context={'identity':{'foo':'bar'}})
		
		
	def test_auth_failed(self):
		"""Raises NotAuthorizedError if the authorization rule fails"""
		with self.assertRaises(errors.NotAuthorizedError):
			api.hiddens.create({}, context={'identity':{}})
			
		with self.assertRaises(errors.NotAuthorizedError):
			api.hiddens.create({}, context={'identity':{'role':'foo'}})
			
			
	def test_auth_pass(self):
		"""Does not raise NotAuthorizedError if the authorization rule passes"""
		storage.create = Mock(return_value={})
		api.hiddens.create({}, context={'identity':{'role':'admin'}})
		
		
	def test_auth_result_fail(self):
		"""Raises NotAuthorizedError if a result rule doesn't pass."""
		api.hiddens.storage.get_by_id = Mock(return_value={'foo':700})
		with self.assertRaises(errors.NotAuthorizedError):
			api.hiddens.get(123)
		
		
	def test_auth_result_pass(self):
		"""Does not raise NotAuthorizedError if a result rule passes."""
		api.hiddens.storage.get_by_id = Mock(return_value={'foo':23})
		api.hiddens.get(123)
		
		
	def test_hidden_result(self):
		"""Hidden fields aren't shown in results."""
		storage.create = Mock(return_value={'_id':'123', 'name':'foo'})
		obj = api.hiddens.create({'name':'foo'}, context={'identity':{'role':'admin'}})
		self.assertNotIn('name', obj)
		
		
	def test_hidden_show_fail(self):
		"""Hidden fields aren't shown in results even when show_hidden=True if the user is not authorized."""
		storage.get_by_id = Mock(return_value={'_id':'123', 'name':'foo', 'foo':23})
		obj = api.hiddens.get('123', show_hidden=True)
		self.assertNotIn('name', obj)
		
		
	def test_hidden_succeed(self):
		"""Hidden fields are shown when show_hidden=True and the user is authorized."""
		storage.get_by_id = Mock(return_value={'_id':'123', 'name':'foo', 'foo':23})
		obj = api.hiddens.get('123', show_hidden=True, context={'identity':{'foo':'bar'}})
		self.assertIn('name', obj)
		
		
	def test_hidden_filter(self):
		"""Can't filter by a hidden field without authorization."""
		storage.check_filter = Mock(side_effect=errors.DisabledFieldError)
		with self.assertRaises(errors.DisabledFieldError):
			api.hiddens.list(filter={'name':'zoomy'}, context={'identity':{}})
		storage.check_filter.assert_called_once_with({'name':'zoomy'}, set(), {'identity': {}})
		
		
	def test_hidden_filter_authorized(self):
		"""Can filter by a hidden field when authorized."""
		storage.check_filter = Mock(return_value=None)
		storage.get = Mock(return_value=[])
		api.hiddens.list(filter={'name':'zoomy'}, context={'identity':{'foo':'bar'}})
		storage.check_filter.assert_called_once_with({'name':'zoomy'}, set(['name']),  {'item': [], 'identity': {'foo': 'bar'}})
		
		
	def test_hidden_sort_fail(self):
		"""Can't sort by a hidden field without authorization."""
		with self.assertRaises(errors.DisabledFieldError) as cm:
			api.hiddens.list(sort=('+name',), context={'identity':{}})
		self.assertEquals(cm.exception.message, 'The "name" field cannot be used for sorting.')
		
		
	def test_authorization_bypass(self):
		"""Can bypass authorization for methods, filters and sort."""
		storage.get = Mock(return_value=[{'name':'zoomy', 'foo':23}])
		results = api.hiddens.list(filter={'name':'zoomy'}, sort=('+name',), bypass_authorization=True, show_hidden=True)
		storage.get.assert_called_once_with(Hidden, sort=('+name',), filter={'name':'zoomy'}, limit=0, offset=0)
		self.assertEquals(results, [{'name':'zoomy', 'foo':23}])
		
		
	def test_entity_hooks(self):
		"""Collections call entity create, update and delete hooks"""
		pre_create = CopyingMock()
		post_create = CopyingMock()
		pre_update = CopyingMock()
		post_update = CopyingMock()
		pre_delete = CopyingMock()
		post_delete = CopyingMock()
		hooks = api.foos.entity.hooks
		hooks.pre('create', pre_create)
		hooks.post('create', post_create)
		hooks.pre('update', pre_update)
		hooks.post('update', post_update)
		hooks.pre('delete', pre_delete)
		hooks.post('delete', post_delete)
		
		context = {'foo':23}
		options = {'bypass_authorization': False, 'fields': {'optional_stuff', 'bazes', 'stuff', 'embedded_foos', 'embedded_bazes', '_id'}, 'allow_embedding': True, 'show_hidden': False, 'context': {'foo': 23}, 'embed': {'embedded_bazes'}, 'can_show_hidden': False}
		
		storage.create = Mock(return_value='123')
		storage.update = Mock(return_value={'_id':'123', 'stuff':'nothings'})
		storage.delete = Mock(return_value=None)
		storage.get_by_id = Mock(return_value={'_id':'123', 'stuff':'nothings'})
		
		foo = api.foos.create({'stuff':'things'}, context=context.copy())
		create_options = deepcopy(options)
		create_options['context']['item'] = foo
		pre_create.assert_called_once_with({'stuff':'things'}, options)
		post_create.assert_called_once_with(foo, create_options)
		
		foo = api.foos.update(foo['_id'], {'stuff':'nothings'}, context=context.copy())
		update_options = deepcopy(options)
		update_options['context']['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'nothings'}, options)
		post_update.assert_called_with(foo, update_options)
		
		foo = api.foos.replace(foo['_id'], {'stuff':'somethings'}, context=context.copy())
		replace_options = deepcopy(options)
		replace_options['context']['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'somethings'}, options)
		post_update.assert_called_with(foo, replace_options)
		
		api.foos.delete(foo['_id'], context=context.copy())
		delete_options = deepcopy(options)
		delete_options['context']['item'] = foo
		pre_delete.assert_called_once_with(foo['_id'], options)
		post_delete.assert_called_once_with(foo['_id'], delete_options)
		
		
	def test_collection_hooks(self):
		"""Collections have create, update and delete hooks"""
		pre_create = CopyingMock()
		post_create = CopyingMock()
		pre_update = CopyingMock()
		post_update = CopyingMock()
		pre_delete = CopyingMock()
		post_delete = CopyingMock()
		hooks = api.foos.hooks
		hooks.pre('create', pre_create)
		hooks.post('create', post_create)
		hooks.pre('update', pre_update)
		hooks.post('update', post_update)
		hooks.pre('delete', pre_delete)
		hooks.post('delete', post_delete)
		context = {'foo':23}
		options = {'bypass_authorization': False, 'fields': {'optional_stuff', 'bazes', 'stuff', 'embedded_foos', 'embedded_bazes', '_id'}, 'allow_embedding': True, 'show_hidden': False, 'context': {'foo': 23}, 'embed': {'embedded_bazes'}, 'can_show_hidden': False}
		
		storage.create = Mock(return_value='123')
		storage.update = Mock(return_value={'_id':'123', 'stuff':'nothings'})
		storage.delete = Mock(return_value=None)
		storage.get_by_id = Mock(return_value={'_id':'123', 'stuff':'nothings'})
		
		foo = api.foos.create({'stuff':'things'}, context=context.copy())
		create_options = deepcopy(options)
		create_options['context']['item'] = foo
		pre_create.assert_called_once_with({'stuff':'things'}, options)
		post_create.assert_called_once_with(foo, create_options)
		
		foo = api.foos.update(foo['_id'], {'stuff':'nothings'}, context=context.copy())
		update_options = deepcopy(options)
		update_options['context']['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'nothings'}, options)
		post_update.assert_called_with(foo, update_options)
		
		foo = api.foos.replace(foo['_id'], {'stuff':'somethings'}, context=context.copy())
		replace_options = deepcopy(options)
		replace_options['context']['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'somethings'}, options)
		post_update.assert_called_with(foo, replace_options)
		
		api.foos.delete(foo['_id'], context=context.copy())
		delete_options = deepcopy(options)
		delete_options['context']['item'] = foo
		pre_delete.assert_called_once_with(foo['_id'], options)
		post_delete.assert_called_once_with(foo['_id'], delete_options)
		
		
	def test_disabled_method(self):
		"""An error is raised when attempting to call a disabled method."""
		with self.assertRaises(errors.DisabledMethodError):
			api.readonly_foos.create({})
		
		
	def test_passes_version(self):
		"""When updating, the _version field is passed through to the storage method"""
		storage.update = Mock(return_value={'_id':'123'})
		storage.get_by_id = Mock(return_value={'_id':'123'})
		api.foos.update('123', {'_version':57})
		storage.update.assert_called_with(Foo, '123', {'_version':57}, replace=False)
		api.foos.replace('123', {'stuff':'things', '_version':57})
		storage.update.assert_called_with(Foo, '123', {'stuff':'things', '_version':57}, replace=True)
		
		
	def test_default_limit(self):
		"""A default limit is used when limit is not passed"""
		storage.get = Mock(return_value=[])
		api.bazes.list()
		storage.get.assert_called_once_with(Baz, sort=(), filter=None, offset=0, limit=10)
		
		
	def test_max_limit(self):
		"""Limit can't exceed max_limit"""
		storage.get = Mock(return_value=[])
		api.bazes.list(limit=50)
		storage.get.assert_called_once_with(Baz, sort=(), filter=None, offset=0, limit=20)
		
		
	def test_default_embedded_not_default(self):
		"""A reference can be embeddable but not embedded"""
		storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		storage.get_by_ids = Mock(return_value=[])
		api.foos.list()
		self.assertFalse(storage.get_by_ids.called)
		
		
	def test_default_not_embedded_not_default_included(self):
		"""A reference that is not embedded by default can still be embedded"""
		storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		storage.get_by_ids = Mock(return_value=[])
		api.foos.list(embed=['embedded_foos'])
		storage.get_by_ids.assert_called_once_with(Foo, ['1','2','3'], sort=(), filter=None, limit=0, offset=0)
		
		
	def test_embeddable_included_if_fields_set(self):
		"""An embeddable field is included if it is in the fields argument"""
		storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		storage.get_by_ids = Mock(return_value=[])
		api.foos.list(fields=['embedded_foos'])
		storage.get_by_ids.assert_called_once_with(Foo, ['1','2','3'], sort=(), filter=None, limit=0, offset=0)
		
		
	def test_embeddable_fields(self):
		"""Only fields in an entity's embedded_fields list are included"""
		storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		storage.get_by_ids = Mock(return_value=[{'_id':'666', 'stuff':123, 'optional_stuff':456}])
		result = api.foos.list(embed=('embedded_foos',))
		self.assertEquals(result, [{'_id':'123', 'embedded_foos':[{'_id':'666', 'stuff':123}]}])
		
		
	def test_field_subset(self):
		"""Can fetch only a subset of fields"""
		storage.get_by_id = CopyingMock(return_value={'_id':'123', 'stuff':123, 'optional_stuff':456})
		result = api.foos.get('123', fields=('optional_stuff',))
		self.assertEquals(result, {'_id':'123', 'optional_stuff':456})
		
		
	def test_no_fields(self):
		"""Only an item's ID is included if fields is an empty list"""
		storage.get_by_id = CopyingMock(return_value={'_id':'123', 'stuff':123, 'optional_stuff':456})
		result = api.foos.get('123', fields=())
		self.assertEquals(result, {'_id':'123'})
		
		
	def test_fields_empty(self):
		"""All of an item's visible fields are returned if the fields list is omitted"""
		foo = {'_id':'123', 'stuff':123, 'optional_stuff':456}
		storage.get_by_id = CopyingMock(return_value=foo)
		result = api.foos.get('123')
		self.assertEquals(result, foo)
		
		
	def test_fields_empty_hidden_field(self):
		"""All of an item's visible fields are returned if the fields list is omitted when an entity has hidden fields"""
		storage.get_by_id = CopyingMock(return_value={'_id':'123', 'name':'hidden', 'foo':23})
		result = api.hiddens.get('123')
		self.assertEquals(result, {'_id':'123', 'foo':23})
		
		
	def test_fields_empty_hidden_list(self):
		"""All of an item's visible fields are returned when listing items"""
		storage.get = CopyingMock(return_value=[{'_id':'123', 'stuff':'foo', 'secret':'i like valuer'}])
		result = api.foos.list()
		self.assertEquals(result, [{'_id':'123', 'stuff':'foo'}])
		
		