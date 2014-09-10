import unittest
from hammock.model import *
from hammock.storage.mongodb import MongoDBStorage


class Foo(Entity):
	a = Text()
	b = TypeOf(int)

storage = MongoDBStorage('test')
model = Model(storage, (Foo,))

class TestMongoDBStorage(unittest.TestCase):
	
	def setUp(self):
		for c in storage.db.collection_names():
			if not c.startswith('system.'):
				storage.db[c].drop()
				
	
	def test_create(self):
		"""
		Should be able to create a document
		"""
		results = list(storage.get(Foo))
		self.assertEquals(len(results), 0)
		
		foo_id = storage.create(Foo, {'a':'cat', 'b':123})
		self.assertIsInstance(foo_id, basestring)
		
		results = list(storage.get(Foo))
		self.assertEquals(len(results), 1)
		self.assertEquals(results[0], {'id':foo_id, 'a':'cat', 'b':123})
		
		
	def test_replace(self):
		"""
		Should be able to replace an existing document
		"""
		foo_id = storage.create(Foo, {'a':'cat', 'b':123})
		storage.update(Foo, foo_id, {'a':'dog'}, replace=True)
		results = list(storage.get(Foo))
		self.assertEquals(results[0], {'id':foo_id, 'a':'dog'})
		
		
	def test_update(self):
		"""
		Should modify an existing document and return the modified version.
		"""
		foo_id = storage.create(Foo, {'a':'cat', 'b':123})
		
		result = storage.update(Foo, foo_id, {'a':'dog'})
		
		results = list(storage.get(Foo))
		self.assertEquals(len(results), 1)
		self.assertEquals(results[0], {'id':foo_id, 'a':'dog', 'b':123})
		
		
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
			doc['id'] = storage.create(Foo, doc)
			
		storage.delete(Foo, docs[1]['id'])
		results = list(storage.get(Foo))
		
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
			doc['id'] = storage.create(Foo, doc)
		
		results = list(storage.get(Foo, filter={'id':docs[0]['id']}))
		self.assertEquals(results,[docs[0]])
		
		results = list(storage.get(Foo, filter={'b':2}))
		self.assertEquals(results,[docs[1]])
		
		results = list(storage.get(Foo, filter={'a':'skidoo', 'b':2}))
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
			doc['id'] = storage.create(Foo, doc)
		
		results = list(storage.get(Foo, filter={'b':{'$gt':1}}))
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
			doc['id'] = storage.create(Foo, doc)
		
		results = list(storage.get(Foo, sort=('+a',)))
		self.assertEquals(results, [docs[3], docs[0], docs[2], docs[1]])
		
		results = list(storage.get(Foo, sort=('-b','-a')))
		self.assertEquals(results, [docs[2], docs[3], docs[1], docs[0]])
		
		
	def test_get_fields(self):
		"""
		Should limit which fields are returned, except for the id field.
		"""
		foo_id = storage.create(Foo, {'a':'one', 'b':1})
		
		result = next(storage.get(Foo, fields=('a',)))
		self.assertEquals(result, {'id':foo_id, 'a':'one'})
		
		result = next(storage.get(Foo, fields=('b',)))
		self.assertEquals(result, {'id':foo_id, 'b':1})
		
		result = next(storage.get(Foo, fields=()))
		self.assertEquals(result, {'id':foo_id})
		
		
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
			doc['id'] = storage.create(Foo, doc)
			
			
		results = list(storage.get(Foo))
		self.assertEquals(len(results), 4)
		
		results = list(storage.get(Foo, limit=2))
		self.assertEquals(len(results), 2)
		
		results = list(storage.get(Foo, offset=1, limit=2))
		self.assertEquals(results, docs[1:3])
		
		
	def test_get_multiple_by_ids(self):
		"""
		Can get a list of documents by id.
		"""
		ids = []
		for i in range(0,10):
			ids.append(storage.create(Foo, {'b':i}))
		
		subset_of_ids = ids[0:5]
		results = list(storage.get_by_ids(Foo, subset_of_ids, fields={}))
		self.assertEquals([r['id'] for r in results], subset_of_ids)