import unittest
from datetime import datetime
from cellardoor.model import *
from cellardoor.storage.mongodb import MongoDBStorage
from cellardoor import errors


class Foo(Entity):
	a = Text()
	b = TypeOf(int)


class Bar(Entity):
	versioned = True
	a = Text()
	b = TypeOf(int)
	
	
class Baz(Entity):
	foo = TypeOf(int, unique=True)
	
	
class Primate(Entity):
	pass
	
	
class Human(Primate):
	name = Text()
	
	
class Scotsman(Human):
	pass


class TestMongoDBStorage(unittest.TestCase):
	
	def setUp(self):
		self.storage = MongoDBStorage('test')
		self.model = Model(self.storage, (Foo, Bar, Baz, Primate, Human, Scotsman))
		
		
	def tearDown(self):
		for c in self.storage.db.collection_names():
			if not c.startswith('system.'):
				self.storage.db[c].drop()
		
	
	def test_create(self):
		"""
		Should be able to create a document
		"""
		results = list(self.storage.get(Foo))
		self.assertEquals(len(results), 0)
		
		foo_id = self.storage.create(Foo, {'a':'cat', 'b':123})
		self.assertIsInstance(foo_id, basestring)
		
		results = list(self.storage.get(Foo))
		self.assertEquals(len(results), 1)
		self.assertEquals(results[0], {'_id':foo_id, 'a':'cat', 'b':123})
		
		
	def test_replace(self):
		"""
		Should be able to replace an existing document
		"""
		foo_id = self.storage.create(Foo, {'a':'cat', 'b':123})
		self.storage.update(Foo, foo_id, {'a':'dog'}, replace=True)
		results = list(self.storage.get(Foo))
		self.assertEquals(results[0], {'_id':foo_id, 'a':'dog'})
		
		
	def test_update(self):
		"""
		Should modify an existing document and return the modified version.
		"""
		foo_id = self.storage.create(Foo, {'a':'cat', 'b':123})
		
		result = self.storage.update(Foo, foo_id, {'a':'dog'})
		
		results = list(self.storage.get(Foo))
		self.assertEquals(len(results), 1)
		self.assertEquals(results[0], {'_id':foo_id, 'a':'dog', 'b':123})
		
		
	def test_delete(self):
		"""
		Should remove the document with the given ID
		"""
		docs = [
			{'a':'one', 'b':1},
			{'a':'two', 'b':2},
			{'a':'three', 'b':3}
		]
		
		for doc in docs:
			doc['_id'] = self.storage.create(Foo, doc)
			
		self.storage.delete(Foo, docs[1]['_id'])
		results = list(self.storage.get(Foo))
		
		self.assertEquals(results, [docs[0], docs[2]])
		
		
	def test_get_filter(self):
		"""
		Should filter results by field value.
		"""
		docs = [
			{'a':'one', 'b':1},
			{'a':'two', 'b':2},
			{'a':'three', 'b':3}
		]
		
		for doc in docs:
			doc['_id'] = self.storage.create(Foo, doc)
		
		results = list(self.storage.get(Foo, filter={'_id':docs[0]['_id']}))
		self.assertEquals(results,[docs[0]])
		
		results = list(self.storage.get(Foo, filter={'b':2}))
		self.assertEquals(results,[docs[1]])
		
		results = list(self.storage.get(Foo, filter={'a':'skidoo', 'b':2}))
		self.assertEquals(results,[])
		
		
	def test_get_filter_fancy(self):
		"""
		Should filter results using mongodb operators.
		"""
		docs = [
			{'a':'one', 'b':1},
			{'a':'two', 'b':2},
			{'a':'three', 'b':3}
		]
		
		for doc in docs:
			doc['_id'] = self.storage.create(Foo, doc)
		
		results = list(self.storage.get(Foo, filter={'b':{'$gt':1}}))
		self.assertEquals(results,docs[1:])
		
		
	def test_get_sort(self):
		"""
		Should sort results by any field(s), ascending or descending.
		"""
		docs = [
			{'a':'one', 'b':1},
			{'a':'two', 'b':2},
			{'a':'three', 'b':3},
			{'a':'four', 'b':3}
		]
		
		for doc in docs:
			doc['_id'] = self.storage.create(Foo, doc)
		
		results = list(self.storage.get(Foo, sort=('+a',)))
		self.assertEquals(results, [docs[3], docs[0], docs[2], docs[1]])
		
		results = list(self.storage.get(Foo, sort=('-b','-a')))
		self.assertEquals(results, [docs[2], docs[3], docs[1], docs[0]])
		
		
	def test_get_fields(self):
		"""
		Should limit which fields are returned, except for the id field.
		"""
		foo_id = self.storage.create(Foo, {'a':'one', 'b':1})
		
		result = next(self.storage.get(Foo, fields=('a',)))
		self.assertEquals(result, {'_id':foo_id, 'a':'one'})
		
		result = next(self.storage.get(Foo, fields=('b',)))
		self.assertEquals(result, {'_id':foo_id, 'b':1})
		
		result = next(self.storage.get(Foo, fields=()))
		self.assertEquals(result, {'_id':foo_id})
		
		
	def test_offset_and_limit(self):
		"""
		Should offset results and limit the number of results returned.
		"""
		docs = [
			{'a':'one', 'b':1},
			{'a':'two', 'b':2},
			{'a':'three', 'b':3},
			{'a':'four', 'b':3}
		]
		
		for doc in docs:
			doc['_id'] = self.storage.create(Foo, doc)
			
			
		results = list(self.storage.get(Foo))
		self.assertEquals(len(results), 4)
		
		results = list(self.storage.get(Foo, limit=2))
		self.assertEquals(len(results), 2)
		
		results = list(self.storage.get(Foo, offset=1, limit=2))
		self.assertEquals(results, docs[1:3])
		
		
	def test_get_multiple_by_ids(self):
		"""
		Can get a list of documents by id.
		"""
		ids = []
		for i in range(0,10):
			ids.append(self.storage.create(Foo, {'b':i}))
		
		subset_of_ids = ids[0:5]
		results = list(self.storage.get_by_ids(Foo, subset_of_ids, fields={}))
		self.assertEquals([r['_id'] for r in results], subset_of_ids)
		
		
	def test_check_filter(self):
		"""
		Raises an error if there are disallowed fields in the filter.
		"""
		filter = {
			'a': 'foo',
			'$or': [{'b':'foo'}, {'c':'bar'}],
			'd': {'$where':'foo()'}
		}
		with self.assertRaises(errors.DisabledFieldError) as cm:
			self.storage.check_filter(filter, ('a','b', 'd'))
		self.assertEquals(cm.exception.message, 'You cannot filter by the "c" field')
		
		
	def test_get_versioned_fail(self):
		"""
		Returns an empty result when trying to get versions of an unversioned entity
		"""
		foo_id = self.storage.create(Foo, {'a':'cat', 'b':123})
		self.storage.update(Foo, foo_id, {'a':'b'})
		results = list(self.storage.get(Foo))
		self.assertEquals(len(results), 1)
		results = list(self.storage.get(Foo, versions=True))
		self.assertEquals(len(results), 0)
		
		
	def test_get_by_ids_versioned_fail(self):
		"""
		Returns an empty result when trying to get versions of an unversioned entity
		"""
		foo_id = self.storage.create(Foo, {'a':'cat', 'b':123})
		self.storage.update(Foo, foo_id, {'a':'b'})
		results = list(self.storage.get_by_ids(Foo, [foo_id]))
		self.assertEquals(len(results), 1)
		results = list(self.storage.get_by_ids(Foo, [foo_id], versions=True))
		self.assertEquals(len(results), 0)
		
		
	def test_create_versioned(self):
		"""
		When created, a versioned entity will have version information.
		"""
		bar_id = self.storage.create(Bar, {'a':'car', 'b':123})
		bar = self.storage.get_by_id(Bar, bar_id)
		self.assertEquals(bar, {'_id':bar_id, '_version':1, 'a':'car', 'b':123})
		
		
	def test_update_versioned_missing_version(self):
		"""
		If the version is not provided with the update, a CompoundValidationError is raised
		"""
		bar_id = self.storage.create(Bar, {'a':'car', 'b':123})
		self.assertRaises(errors.CompoundValidationError, self.storage.update, Bar, bar_id, {'a':'bike'})
		
		
	def test_update_versioned_conflict(self):
		"""
		If the version provided with an update doesn't match the version of the stored document, a VersionConflictError is raised.
		"""
		bar_id = self.storage.create(Bar, {'a':'car', 'b':123})
		bar = self.storage.get_by_id(Bar, bar_id)
		with self.assertRaises(errors.VersionConflictError) as cm:
			self.storage.update(Bar, bar_id, {'_version':99, 'a':'bike'})
		self.assertEquals(cm.exception.other, bar)
		
		
	def test_update_versioned(self):
		"""
		When a versioned item is updated, the version number will increment.
		"""
		bar_id = self.storage.create(Bar, {'a':'car', 'b':123})
		bar = self.storage.update(Bar, bar_id, {'_version':1, 'a':'bike'})
		self.assertEquals(bar['_version'], 2)
		bar = self.storage.update(Bar, bar_id, {'_version':2, 'a':'unicycle'})
		self.assertEquals(bar['_version'], 3)
		
		
	def test_versioned_get(self):
		"""
		Can get a list of past versions of documents
		"""
		bar_id = self.storage.create(Bar, {'a':'car', 'b':123})
		self.storage.update(Bar, bar_id, {'_version':1, 'a':'bike'})
		self.storage.update(Bar, bar_id, {'_version':2, 'a':'unicycle'})
		results = list(self.storage.get(Bar, versions=True))
		self.assertEquals(
			results,
			[
				{'_id':bar_id, '_version':1, 'a':'car', 'b':123},
				{'_id':bar_id, '_version':2, 'a':'bike', 'b':123}
			]
		)
		
		
	def test_versioned_delete(self):
		"""
		Deleting a versioned document leaves a record of the deletion.
		"""
		bar_id = self.storage.create(Bar, {'a':'bike', 'b':123})
		bar = self.storage.get_by_id(Bar, bar_id)
		self.storage.delete(Bar, bar_id, deleted_by='The Grinch')
		results = list(self.storage.get(Bar, versions=True))
		self.assertEquals(results[0], bar)
		delete_record = results[1]
		self.assertIn('_deleted_on', delete_record)
		self.assertIsInstance(delete_record['_deleted_on'], datetime)
		del delete_record['_deleted_on']
		self.assertEquals(delete_record, {'_id':bar_id, '_version':2, '_deleted_by':'The Grinch'})
		
		
	def test_inheritance_type_name(self):
		"""
		Entities that extend other entities get a _type field
		"""
		sean_id = self.storage.create(Scotsman, {'name':'Sean Connery'})
		sean = self.storage.get_by_id(Scotsman, sean_id)
		self.assertEquals(sean['_type'], 'Primate.Human.Scotsman')
		
		
	def test_inheritance_polymorphism(self):
		"""
		Can get subclass items by querying the base class
		"""
		sean_id = self.storage.create(Scotsman, {'name':'Sean Connery'})
		sean = self.storage.get_by_id(Scotsman, sean_id)
		base_sean = self.storage.get_by_id(Human, sean_id)
		self.assertEquals(base_sean, sean)
		humans = list(self.storage.get(Human))
		self.assertEquals(humans, [sean])
		
		
	def test_inheritance_filtering(self):
		"""
		When fetching items for a subclass, no base class items are returned.
		"""
		bobo_id = self.storage.create(Primate, {})
		bobo = self.storage.get_by_id(Primate, bobo_id)
		not_bobo = self.storage.get_by_id(Human, bobo_id)
		self.assertEquals(not_bobo, None)
		
		sean_id = self.storage.create(Scotsman, {'name':'Sean Connery'})
		sean = self.storage.get_by_id(Scotsman, sean_id)
		
		primate_results = list(self.storage.get(Primate))
		human_results = list(self.storage.get(Human))
		self.assertEquals(primate_results, [bobo, sean])
		self.assertEquals(human_results, [sean])
		
		
	def test_create_collision(self):
		"""
		Raises an error when attempting to create an item with a duplicated unique field.
		"""
		self.storage.create(Baz, {'foo':123})
		
		with self.assertRaises(errors.DuplicateError):
			self.storage.create(Baz, {'foo':123})
			
			
	def test_update_collision(self):
		"""
		Raises an error when attempting to update an item with a duplicated unique field.
		"""
		self.storage.create(Baz, {'foo':123})
		baz_id = self.storage.create(Baz, {'foo':321})
		
		with self.assertRaises(errors.DuplicateError):
			self.storage.update(Baz, baz_id, {'foo':123})
		
		
	def test_nonnative_ids(self):
		"""
		Can use something other than a `bson.objectid.ObjectId` as an item id.
		"""
		baz_id = self.storage.create(Baz, {'_id':123, 'foo':123})
		self.assertEquals(baz_id, '123')
		
		fetched_baz = self.storage.get_by_id(Baz, '123')
		self.assertEquals(fetched_baz, {'_id':'123', 'foo':123})
		
		udpated_baz = self.storage.update(Baz, '123', {'foo':666})
		self.assertEquals(udpated_baz, {'_id':'123', 'foo':666})
		
		self.storage.delete(Baz, '123')
		fetched_baz = self.storage.get_by_id(Baz, '123')
		self.assertEquals(fetched_baz, None)
		