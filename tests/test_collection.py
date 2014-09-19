import unittest
from copy import deepcopy
from mock import Mock
from bson.objectid import ObjectId
from hammock.model import Model, Entity, Reference, Link, Text, ListOf, TypeOf
from hammock.collection import Collection
from hammock.methods import ALL, LIST, GET, CREATE
from hammock.storage.mongodb import MongoDBStorage
from hammock import errors, Hammock
from hammock import auth


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
	embedded_bazes = ListOf(Reference('Baz', embedded=True))
	
	
class Bar(Entity):
	foo = Reference(Foo)
	embedded_foo = Reference(Foo, embedded=True)
	bazes = ListOf(Reference('Baz'))
	number = TypeOf(int)
	name = Text()
	
	
class Baz(Entity):
	name = Text(required=True)
	foo = Link(Foo, 'bazes', multiple=False)
	embedded_foo = Link(Foo, 'bazes', multiple=False, embedded=True)
	
	
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
		'embedded_bazes': 'BazesCollection'
	}
	enabled_filters = ('stuff',)
	enabled_sort = ('stuff',)
	
	
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
	
	
class CollectionTest(unittest.TestCase):
	
	def setUp(self):
		self.storage = MongoDBStorage('test')
		for c in self.storage.db.collection_names():
			if not c.startswith('system.'):
				self.storage.db[c].drop()
		super(CollectionTest, self).setUp()
		self.api = Hammock(collections=(FoosCollection, BarsCollection, BazesCollection, HiddenCollection, ReadOnlyFoosCollection),
						   storage=self.storage)
		
		
	def test_create_fail_validation(self):
		"""
		Fails if the request fields don't pass validation.
		"""
		with self.assertRaises(errors.CompoundValidationError):
			self.api.foos.create({})
	
	
	def test_create_succeed(self):
		"""
		Creates a new item in persistent storage if we pass validation.
		"""
		foo = self.api.foos.create({'stuff':'foo'})
		self.assertIn('_id', foo)
		foo_id = foo['_id']
		del foo['_id']
		self.assertEquals(foo, {'stuff':'foo'})
		
		
	def test_list(self):
		"""
		Returns a list of created items
		"""
		saved_foos = []
		
		for i in range(0,3):
			saved_foos.append(
				self.api.foos.create({'stuff':'foo#%d' % i})
			)
		
		fetched_foos = list(self.api.foos.list())
		self.assertEquals(fetched_foos, saved_foos)
		
		
	def test_get(self):
		"""
		Can get a single item
		"""
		foo = self.api.foos.create({'stuff':'123'})
		fetched_foo = self.api.foos.get(foo['_id'])
		self.assertEquals(fetched_foo, foo)
		
		
	def test_get_nonexistent(self):
		"""
		Trying to fetch a nonexistent item raises an error.
		"""
		with self.assertRaises(errors.NotFoundError):
			self.api.foos.get(str(ObjectId()))
		
		
	def test_update(self):
		"""
		Can update a subset of fields
		"""
		foo = self.api.foos.create({'stuff':'foo'})
		new_foo = self.api.foos.update(foo['_id'], {'stuff':'baz'})
		self.assertEquals(foo['_id'], new_foo['_id'])
		self.assertEquals(new_foo['stuff'], 'baz')
		fetched_foo = self.api.foos.get(foo['_id'])
		self.assertEquals(new_foo, fetched_foo)
		
		
	def test_update_nonexistent(self):
		"""
		Trying to update a nonexistent item raises an error.
		"""
		with self.assertRaises(errors.NotFoundError):
			self.api.foos.update(str(ObjectId()), {})
		
		
	def test_replace(self):
		"""
		Can replace a whole existing item
		"""
		foo = self.api.foos.create({'stuff':'foo', 'optional_stuff':'bar'})
		self.api.foos.replace(foo['_id'], {'stuff':'baz'})
		new_foo = self.api.foos.get(foo['_id'])
		self.assertEquals(new_foo, {'stuff': 'baz', '_id':foo['_id']})
		
		
	def test_replace_nonexistent(self):
		"""
		Trying to replace a nonexistent item raises an error.
		"""
		foo_id = str(ObjectId())
		with self.assertRaises(errors.NotFoundError):
			self.api.foos.replace(foo_id, {'stuff':'things'})
		
		
	def test_delete(self):
		"""
		Can remove an existing item
		"""
		foo = self.api.foos.create({'stuff':'123'})
		self.api.foos.delete(foo['_id'])
		with self.assertRaises(errors.NotFoundError):
			self.api.foos.get(foo['_id'])
		
		
	def test_single_reference_validation_fail(self):
		"""
		Fails validation if setting a reference to a non-existent ID.
		"""
		with self.assertRaises(errors.CompoundValidationError):
			bar = self.api.bars.create({'foo':str(ObjectId())})
		
		
	def test_single_reference(self):
		"""
		Can get a reference through a link.
		"""
		foo = self.api.foos.create({'stuff':'foo', 'optional_stuff':'bar'})
		bar = self.api.bars.create({'foo':foo['_id']})
		
		linked_foo = self.api.bars.link(bar['_id'], 'foo')
		self.assertEquals(linked_foo, foo)
		
		
	def test_single_reference_get_embedded(self):
		"""
		Embedded references are included when fetching the referencing item.
		"""
		foo = self.api.foos.create({'stuff':'foo', 'optional_stuff':'bar'})
		bar = self.api.bars.create({'embedded_foo':foo['_id']})
		self.assertEquals(bar['embedded_foo'], foo)
		
		
	def test_multiple_reference(self):
		"""
		Can set a list of references when creating an item
		"""
		created_bazes = []
		for i in range(0,3):
			created_bazes.append(
				self.api.bazes.create({'name':'Baz#%d' % i})
			)
		
		foo = self.api.foos.create({'stuff':'things', 'bazes':[x['_id'] for x in created_bazes]})
		linked_bazes = self.api.foos.link(foo['_id'], 'bazes')
		self.assertEquals(linked_bazes, created_bazes)
		
		
	def test_multiple_reference_get_embedded(self):
		"""
		Embedded reference list is included when fetching the referencing item.
		"""
		created_bazes = []
		for i in range(0,3):
			created_bazes.append(
				self.api.bazes.create({'name':'Baz#%d' % i})
			)
		
		foo = self.api.foos.create({'stuff':'things', 'embedded_bazes':[x['_id'] for x in created_bazes]})
		self.assertEquals(foo['embedded_bazes'], created_bazes)
		
		
	def test_single_link(self):
		"""
		Can resolve a single link the same way as a reference.
		"""
		bazes = []
		
		for i in range(0,3):
			bazes.append(self.api.bazes.create({'name':'Baz#%d' % i}))
		
		baz_ids = [x['_id'] for x in bazes]
		foo = self.api.foos.create({'stuff': 'things', 'bazes':baz_ids})
		linked_foo = self.api.bazes.link(baz_ids[0], 'foo')
		self.assertEquals(linked_foo, foo)
		
		
	def test_single_link_embedded(self):
		"""
		Single embedded links are automatically resolved.
		"""
		baz_ids = []
		
		for i in range(0,3):
			baz = self.api.bazes.create({'name':'Baz#%d' % i})
			baz_ids.append(baz['_id'])
		
		foo = self.api.foos.create({'stuff': 'things', 'bazes':baz_ids})
		baz = self.api.bazes.get(baz_ids[0])
		self.assertEquals(baz['embedded_foo'], foo)
		
		
	def test_multiple_link(self):
		"""
		Can resolve a multiple link the same way as a reference.
		"""
		foo = self.api.foos.create({'stuff':'foo'})
		
		bars = []
		for i in range(0,3):
			bars.append(
				self.api.bars.create({'foo':foo['_id']})
			)
			
		linked_bars = self.api.foos.link(foo['_id'], 'bars')
		self.assertEquals(linked_bars, bars)
		
		
	def test_filter_disabled_error(self):
		"""
		An error is raised when attempting to filter by a disabled filter field.
		"""
		with self.assertRaises(errors.DisabledFieldError):
			self.api.foos.list(filter={'optional_stuff':'cake'})
		
		
	def test_filter(self):
		"""
		Only returns results matching the filter.
		"""
		foos = []
		
		for i in range(0,5):
			foos.append(self.api.foos.create({'stuff':'Foo#%d' % i}))
		
		items = list(self.api.foos.list(filter={'stuff':'Foo#1'}))
		self.assertEquals(items, [foos[1]])
		
		
	def test_filtered_reference(self):
		"""
		Can filter referenced items.
		"""
		bazes = []
		for i in range(0,3):
			bazes.append(
				self.api.bazes.create({'name':'Baz#%d' % i})
			)
		
		foo = self.api.foos.create(
			{'stuff':'foo', 'bazes':[x['_id'] for x in bazes]}
		)
		
		items = self.api.foos.link(foo['_id'], 'bazes', filter={'name':{'$in':['Baz#1', 'Baz#2']}})
		self.assertEquals([x['_id'] for x in items], [x['_id'] for x in bazes[1:]])
		
		
	def test_filtered_link(self):
		"""
		Can filter linked items.
		"""
		foo = self.api.foos.create({'stuff':'foo'})
		
		bars = []
		for i in range(0,3):
			bars.append(
				self.api.bars.create({'foo':foo['_id'], 'number':i})
			)
		
		items = self.api.foos.link(foo['_id'], 'bars', filter={'number':{'$gt':0}})
		self.assertEquals([x['_id'] for x in items], [x['_id'] for x in bars[1:]])
		
		
	def test_sort_fail(self):
		"""
		Trying to sort by a sort-disabled field raises an error.
		"""
		with self.assertRaises(errors.DisabledFieldError) as cm:
			self.api.foos.list(sort=('+optional_stuff',))
		
		
	def test_sort(self):
		"""
		Can sort items
		"""
		bars = []
		for i in range(0,5):
			bars.append(
				self.api.bars.create({'number':i, 'name':'%d' % (5-i)})
			)
		
		items = self.api.bars.list(sort=('+number',))
		self.assertEquals(items, bars)
		
		
	def test_sort_default(self):
		"""
		If no sort is set, the default is used.
		"""
		bars = []
		for i in range(0,5):
			bars.append(
				self.api.bars.create({'number':i, 'name':'%d' % (5-i)})
			)
		bars.reverse()
		items = self.api.bars.list()
		self.assertEquals(items, bars)
	
		
	def test_sorted_reference(self):
		"""
		Can sort referenced items.
		"""
		bazes = []
		for i in range(0,3):
			bazes.append(
				self.api.bazes.create({'name':'Baz#%d' % i})
			)
		
		foo = self.api.foos.create({'stuff':'foo', 'bazes':[x['_id'] for x in bazes]})
		items = self.api.foos.link(foo['_id'], 'bazes', sort=('-name',))
		bazes.reverse()
		self.assertEquals(items, bazes)
		
		
	def test_sorted_link(self):
		"""
		Can sort linked items.
		"""
		foo = self.api.foos.create({'stuff':'foo'})
		
		bars = []
		for i in range(0,3):
			bars.append(
				self.api.bars.create({'foo':foo['_id'], 'number':i})
			)
			
		items = self.api.foos.link(foo['_id'], 'bars', sort=('-number',))
		bars.reverse()
		self.assertEquals(items, bars)
		
		
	def test_offset_and_limit(self):
		"""
		Can skip some items and limit the number of items
		"""
		foos = []
		for i in range(0,5):
			foos.append(
				self.api.foos.create({'stuff':'Foo#%d' % i})
			)
		
		items = self.api.foos.list(offset=1, limit=1)
		self.assertEquals(items, [foos[1]])
		
		
	def test_offset_and_limit_reference(self):
		"""
		Can skip and limit referenced items.
		"""
		bazes = []
		for i in range(0,3):
			bazes.append(
				self.api.bazes.create({'name':'Baz#%d' % i})
			)
		
		foo = self.api.foos.create({'stuff':'foo', 'bazes':[x['_id'] for x in bazes]})
		
		items = self.api.foos.link(foo['_id'], 'bazes', offset=1, limit=1)
		bazes.reverse()
		self.assertEquals(items, [bazes[1]])
		
		
	def test_offset_and_limit_link(self):
		"""
		Can skip and limit linked items.
		"""
		foo = self.api.foos.create({'stuff':'foo'})
		
		bars = []
		for i in range(0,3):
			bars.append(
				self.api.bars.create({'foo':foo['_id'], 'number':i})
			)
		
		items = self.api.foos.link(foo['_id'], 'bars', offset=1, limit=1)
		bars.reverse()
		self.assertEquals(items, [bars[1]])
		
		
	def test_auth_required_not_present(self):
		"""Raise NotAuthenticatedError if authorization requires authentication and it is not present."""
		with self.assertRaises(errors.NotAuthenticatedError):
			self.api.hiddens.list()
			
			
	def test_auth_required_present(self):
		"""Don't raise NotAuthenticatedError if authentication is required and present."""
		self.api.hiddens.list(context={'identity':{'foo':'bar'}})
		
		
	def test_auth_failed(self):
		"""Raises NotAuthorizedError if the authorization rule fails"""
		with self.assertRaises(errors.NotAuthorizedError):
			self.api.hiddens.create({}, context={'identity':{}})
			
		with self.assertRaises(errors.NotAuthorizedError):
			self.api.hiddens.create({}, context={'identity':{'role':'foo'}})
			
			
	def test_auth_pass(self):
		"""Does not raise NotAuthorizedError if the authorization rule passes"""
		obj = self.api.hiddens.create({}, context={'identity':{'role':'admin'}})
		self.assertIn('_id', obj)
		
		
	def test_auth_result_fail(self):
		"""Raises NotAuthorizedError if a result rule doesn't pass."""
		self.api.hiddens.storage.get_by_id = Mock(return_value={'foo':700})
		with self.assertRaises(errors.NotAuthorizedError):
			self.api.hiddens.get(123)
		
		
	def test_auth_result_pass(self):
		"""Does not raise NotAuthorizedError if a result rule passes."""
		self.api.hiddens.storage.get_by_id = Mock(return_value={'foo':23})
		self.api.hiddens.get(123)
		
		
	def test_hidden_result(self):
		"""Hidden fields aren't shown in results."""
		obj = self.api.hiddens.create({'name':'foo'}, context={'identity':{'role':'admin'}})
		self.assertNotIn('name', obj)
		
		
	def test_hidden_show_fail(self):
		"""Hidden fields aren't shown in results even when show_hidden=True if the user is not authorized."""
		obj = self.api.hiddens.create({'name':'pokey', 'foo':23}, context={'identity':{'role':'admin'}})
		obj = self.api.hiddens.get(obj['_id'], show_hidden=True)
		self.assertNotIn('name', obj)
		
		
	def test_hidden_succeed(self):
		"""Hidden fields are shown when show_hidden=True and the user is authorized."""
		obj = self.api.hiddens.create({'name':'pokey', 'foo':23}, context={'identity':{'role':'admin'}})
		obj = self.api.hiddens.get(obj['_id'], show_hidden=True, context={'identity':{'foo':'bar'}})
		self.assertIn('name', obj)
		
		
	def test_hidden_filter(self):
		"""Can't filter by a hidden field without authorization."""
		with self.assertRaises(errors.DisabledFieldError):
			self.api.hiddens.list(filter={'name':'zoomy'}, context={'identity':{}})
		
		
	def test_hidden_filter_authorized(self):
		"""Can filter by a hidden field when authorized."""
		self.api.hiddens.create({'name':'poky', 'foo':23}, context={'identity':{'role':'admin'}})
		self.api.hiddens.create({'name':'zoomy', 'foo':23}, context={'identity':{'role':'admin'}})
		results = list(self.api.hiddens.list(filter={'name':'zoomy'}, context={'identity':{'foo':'bar'}}))
		self.assertEquals(len(results), 1)
		
		
	def test_hidden_sort_fail(self):
		"""Can't sort by a hidden field without authorization."""
		with self.assertRaises(errors.DisabledFieldError) as cm:
			self.api.hiddens.list(sort=('+name',), context={'identity':{}})
		self.assertEquals(cm.exception.message, 'The "name" field cannot be used for sorting.')
		
		
	def test_entity_hooks(self):
		"""Collections call entity create, update and delete hooks"""
		pre_create = Mock()
		post_create = Mock()
		pre_update = Mock()
		post_update = Mock()
		pre_delete = Mock()
		post_delete = Mock()
		hooks = self.api.foos.entity.hooks
		hooks.pre('create', pre_create)
		hooks.post('create', post_create)
		hooks.pre('update', pre_update)
		hooks.post('update', post_update)
		hooks.pre('delete', pre_delete)
		hooks.post('delete', post_delete)
		
		foo = self.api.foos.create({'stuff':'things'})
		pre_create.assert_called_with({'stuff':'things'})
		post_create.assert_called_with(foo)
		
		foo = self.api.foos.update(foo['_id'], {'stuff':'nothings'})
		pre_update.assert_called_with(foo['_id'], {'stuff':'nothings'}, replace=False)
		post_update.assert_called_with(foo, replace=False)
		
		foo = self.api.foos.replace(foo['_id'], {'stuff':'somethings'})
		pre_update.assert_called_with(foo['_id'], {'stuff':'somethings'}, replace=True)
		post_update.assert_called_with(foo, replace=True)
		
		self.api.foos.delete(foo['_id'])
		pre_delete.assert_called_with(foo['_id'])
		post_delete.assert_called_with(foo['_id'])
		
		
	def test_collection_hooks(self):
		"""Collections have create, update and delete hooks"""
		pre_create = CopyingMock()
		post_create = Mock()
		pre_update = CopyingMock()
		post_update = Mock()
		pre_delete = CopyingMock()
		post_delete = Mock()
		hooks = self.api.foos.hooks
		hooks.pre('create', pre_create)
		hooks.post('create', post_create)
		hooks.pre('update', pre_update)
		hooks.post('update', post_update)
		hooks.pre('delete', pre_delete)
		hooks.post('delete', post_delete)
		context = {'foo':23}
		
		foo = self.api.foos.create({'stuff':'things'}, context=context.copy())
		create_context = context.copy()
		create_context['item'] = foo
		pre_create.assert_called_with({'stuff':'things'}, context=context)
		post_create.assert_called_with(foo, context=create_context)
		
		foo = self.api.foos.update(foo['_id'], {'stuff':'nothings'}, context=context.copy())
		update_context = context.copy()
		update_context['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'nothings'}, replace=False, context=context)
		post_update.assert_called_with(foo, context=update_context, replace=False)
		
		foo = self.api.foos.replace(foo['_id'], {'stuff':'somethings'}, context=context.copy())
		replace_context = context.copy()
		replace_context['item'] = foo
		pre_update.assert_called_with(foo['_id'], {'stuff':'somethings'}, replace=True, context=context)
		post_update.assert_called_with(foo, context=replace_context, replace=True)
		
		self.api.foos.delete(foo['_id'], context=context.copy())
		delete_context = context.copy()
		delete_context['item'] = foo
		pre_delete.assert_called_with(foo['_id'], context=context)
		post_delete.assert_called_with(foo['_id'], context=delete_context)
		
		
	def test_disabled_method(self):
		"""An error is raised when attempting to call a disabled method."""
		with self.assertRaises(errors.DisabledMethodError):
			self.api.readonly_foos.create({})
		
		