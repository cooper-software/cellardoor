import unittest
from mock import Mock
from bson.objectid import ObjectId
from hammock.model import Model, Entity, Reference, Link, Text, ListOf, TypeOf
from hammock.collection import Collection
from hammock.methods import ALL, LIST, GET, CREATE
from hammock.storage.mongodb import MongoDBStorage
from hammock import errors, Hammock
from hammock import auth


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
	
	
class Baz(Entity):
	name = Text(required=True)
	foo = Link(Foo, 'bazes', multiple=False)
	embedded_foo = Link(Foo, 'bazes', multiple=False, embedded=True)
	
	
class Hidden(Entity):
	name = Text(hidden=True)
	

class FoosCollection(Collection):
	entity = Foo
	enabled_methods = ALL
	links = {
		'bars': 'BarsCollection',
		'bazes': 'BazesCollection',
		'embedded_bazes': 'BazesCollection'
	}
	enabled_filters = ('stuff',)
	
	
class BarsCollection(Collection):
	entity = Bar
	enabled_methods = ALL
	links = {
		'foo': FoosCollection,
		'embedded_foo': FoosCollection,
		'bazes': 'BazesCollection'
	}
	enabled_filters = ('number',)
	
	
class BazesCollection(Collection):
	entity = Baz
	plural_name = 'bazes'
	enabled_methods = ALL
	links = {
		'foo': FoosCollection,
		'embedded_foo': FoosCollection
	}
	
	
class HiddenCollection(Collection):
	entity = Hidden
	enabled_methods = ALL
	method_authorization = (
		((LIST,), auth.identity.exists()),
		((CREATE,), auth.identity.role == 'admin'),
		((GET,), auth.result.foo == 23)
	)
	

model = Model(None, (Foo, Bar, Baz))

class CollectionTest(unittest.TestCase):
	
	def setUp(self):
		self.storage = MongoDBStorage('test')
		for c in self.storage.db.collection_names():
			if not c.startswith('system.'):
				self.storage.db[c].drop()
		super(CollectionTest, self).setUp()
		self.api = Hammock(collections=(FoosCollection, BarsCollection, BazesCollection, HiddenCollection),
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
		self.assertIn('id', foo)
		foo_id = foo['id']
		del foo['id']
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
		fetched_foo = self.api.foos.get(foo['id'])
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
		new_foo = self.api.foos.update(foo['id'], {'stuff':'baz'})
		self.assertEquals(foo['id'], new_foo['id'])
		self.assertEquals(new_foo['stuff'], 'baz')
		fetched_foo = self.api.foos.get(foo['id'])
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
		self.api.foos.replace(foo['id'], {'stuff':'baz'})
		new_foo = self.api.foos.get(foo['id'])
		self.assertEquals(new_foo, {'stuff': 'baz', 'id':foo['id']})
		
		
	def test_replace_nonexistent(self):
		"""
		Trying to replace a nonexistent item creates it.
		"""
		foo_id = str(ObjectId())
		self.api.foos.replace(foo_id, {'stuff':'things'})
		foo = self.api.foos.get(foo_id)
		self.assertEquals(foo, {'stuff':'things', 'id':foo_id})
		
		
	def test_delete(self):
		"""
		Can remove an existing item
		"""
		foo = self.api.foos.create({'stuff':'123'})
		self.api.foos.delete(foo['id'])
		with self.assertRaises(errors.NotFoundError):
			self.api.foos.get(foo['id'])
		
		
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
		bar = self.api.bars.create({'foo':foo['id']})
		
		linked_foo = self.api.bars.link(bar['id'], 'foo')
		self.assertEquals(linked_foo, foo)
		
		
	def test_single_reference_get_embedded(self):
		"""
		Embedded references are included when fetching the referencing item.
		"""
		foo = self.api.foos.create({'stuff':'foo', 'optional_stuff':'bar'})
		bar = self.api.bars.create({'embedded_foo':foo['id']})
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
		
		foo = self.api.foos.create({'stuff':'things', 'bazes':[x['id'] for x in created_bazes]})
		linked_bazes = self.api.foos.link(foo['id'], 'bazes')
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
		
		foo = self.api.foos.create({'stuff':'things', 'embedded_bazes':[x['id'] for x in created_bazes]})
		self.assertEquals(foo['embedded_bazes'], created_bazes)
		
		
	def test_single_link(self):
		"""
		Can resolve a single link the same way as a reference.
		"""
		bazes = []
		
		for i in range(0,3):
			bazes.append(self.api.bazes.create({'name':'Baz#%d' % i}))
		
		baz_ids = [x['id'] for x in bazes]
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
			baz_ids.append(baz['id'])
		
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
				self.api.bars.create({'foo':foo['id']})
			)
			
		linked_bars = self.api.foos.link(foo['id'], 'bars')
		self.assertEquals(linked_bars, bars)
		
		
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
			{'stuff':'foo', 'bazes':[x['id'] for x in bazes]}
		)
		
		items = self.api.foos.link(foo['id'], 'bazes', filter={'name':{'$in':['Baz#1', 'Baz#2']}})
		self.assertEquals([x['id'] for x in items], [x['id'] for x in bazes[1:]])
		
		
	def test_filtered_link(self):
		"""
		Can filter linked items.
		"""
		foo = self.api.foos.create({'stuff':'foo'})
		
		bars = []
		for i in range(0,3):
			bars.append(
				self.api.bars.create({'foo':foo['id'], 'number':i})
			)
		
		items = self.api.foos.link(foo['id'], 'bars', filter={'number':{'$gt':0}})
		self.assertEquals([x['id'] for x in items], [x['id'] for x in bars[1:]])
		
		
	def test_sort(self):
		"""
		Can sort items
		"""
		foos = []
		for i in range(0,5):
			foos.append(
				self.api.foos.create({'stuff':'Foo#%d' % i})
			)
		
		items = self.api.foos.list(sort=('-stuff',))
		foos.reverse()
		self.assertEquals(items, foos)
		
		
	def test_sorted_reference(self):
		"""
		Can sort referenced items.
		"""
		bazes = []
		for i in range(0,3):
			bazes.append(
				self.api.bazes.create({'name':'Baz#%d' % i})
			)
		
		foo = self.api.foos.create({'stuff':'foo', 'bazes':[x['id'] for x in bazes]})
		items = self.api.foos.link(foo['id'], 'bazes', sort=('-name',))
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
				self.api.bars.create({'foo':foo['id'], 'number':i})
			)
			
		items = self.api.foos.link(foo['id'], 'bars', sort=('-number',))
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
		
		foo = self.api.foos.create({'stuff':'foo', 'bazes':[x['id'] for x in bazes]})
		
		items = self.api.foos.link(foo['id'], 'bazes', offset=1, limit=1)
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
				self.api.bars.create({'foo':foo['id'], 'number':i})
			)
		
		items = self.api.foos.link(foo['id'], 'bars', offset=1, limit=1)
		bars.reverse()
		self.assertEquals(items, [bars[1]])
		
		
	def test_auth_required_not_present(self):
		"""Raise NotAuthenticatedError if authorization requires authentication and it is not present."""
		with self.assertRaises(errors.NotAuthenticatedError):
			self.api.hiddens.list()
			
			
	def test_auth_required_present(self):
		"""Don't raise NotAuthenticatedError if authentication is required and present."""
		self.api.hiddens.list(context={'identity':{}})
		
		
	def test_auth_failed(self):
		"""Raises NotAuthorizedError if the authorization rule fails"""
		with self.assertRaises(errors.NotAuthorizedError):
			self.api.hiddens.create({}, context={'identity':{}})
			
		with self.assertRaises(errors.NotAuthorizedError):
			self.api.hiddens.create({}, context={'identity':{'role':'foo'}})
			
			
	def test_auth_pass(self):
		"""Does not raise NotAuthorizedError if the authorization rule passes"""
		obj = self.api.hiddens.create({}, context={'identity':{'role':'admin'}})
		self.assertIn('id', obj)
		
		
	def test_auth_result_fail(self):
		"""Raises NotAuthorizedError if a result rule doesn't pass."""
		self.api.hiddens.storage.get_by_id = Mock(return_value={'foo':700})
		with self.assertRaises(errors.NotAuthorizedError):
			self.api.hiddens.get(123)
		
		
	def test_auth_result_pass(self):
		"""Does not raise NotAuthorizedError if a result rule passes."""
		self.api.hiddens.storage.get_by_id = Mock(return_value={'foo':23})
		self.api.hiddens.get(123)
		