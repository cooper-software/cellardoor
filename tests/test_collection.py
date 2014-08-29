import unittest
import mongoengine as me
from bson.objectid import ObjectId
from hammock import Collection
from hammock.errors import NotAuthorizedError, NotAllowedError, ParameterError

class TestDoc(me.Document):
	name = me.StringField()
	another_field = me.IntField()


me.connect('hammock_test')


class TestCollection(unittest.TestCase):

	def setUp(self):
		TestDoc.objects().delete()


	def generate_collection(self, n=20):
		class TestDocCollection(Collection):
			document = TestDoc

		docs = []
		for i in range(0, n):
			doc = TestDoc(name='doc#%02d' % i, another_field=n-i)
			doc.save()
			docs.append(doc)

		return TestDocCollection, docs


	def test_identity(self):
		class TestDocCollection(Collection):
			document = TestDoc

		identity = {'foo':'bar'}
		testdocs = TestDocCollection(identity)
		self.assertEquals(testdocs.identity, identity)


	def test_list_limits_and_skip(self):
		TestDocCollection, docs = self.generate_collection(n=20)

		self.assertEquals(TestDoc.objects().count(), 20)
		
		TestDocCollection.default_limit = 10
		TestDocCollection.max_limit = 15
		testdocs = TestDocCollection()

		# No limit argument fetches the default limit
		results = list(testdocs.list())
		self.assertEquals(len(results), testdocs.default_limit)

		# The limit argument works
		results = list(testdocs.list(limit=5))
		self.assertEquals(len(results), 5)

		results = list(testdocs.list(limit=15))
		self.assertEquals(len(results), 15)

		# max_limit is the ceiling regardless of the limits arg
		results = list(testdocs.list(limit=100))
		self.assertEquals(len(results), 15)

		# skip works
		results = list(testdocs.list(skip=3, limit=1))
		self.assertEquals(results[0].name, 'doc#03')
		
		# skip and limit have to be ints
		with self.assertRaises(ParameterError):
			testdocs.list(skip='olives')
			
		with self.assertRaises(ParameterError):
			testdocs.list(limit='artichokes')


	def test_list_fields(self):
		TestDoc(name='foo', another_field=23).save()
		
		class TestDocCollection(Collection):
			document = TestDoc

		testdocs = TestDocCollection()

		# fields exclusively includes the listed fields
		doc = testdocs.list(fields=('name',)).first().to_mongo()
		self.assertEquals(doc.get('name'), 'foo')
		self.assertEquals(doc.get('another_field'), None)
		
		# fields have to be lists or tuples of strings
		with self.assertRaises(ParameterError):
			testdocs.list(fields='olives')
			
		with self.assertRaises(ParameterError):
			testdocs.list(fields=(1,3))


	def test_list_sort(self):
		TestDocCollection, docs = self.generate_collection(n=20)
		testdocs = TestDocCollection()

		# ascending by name
		doc = testdocs.list(sort=('+name',)).first()
		self.assertEquals(doc.id, docs[0].id)

		# descending by name
		doc = testdocs.list(sort=('-name',)).first()
		self.assertEquals(doc.id, docs[19].id)

		# ascending by another_field
		doc = testdocs.list(sort=('+another_field',)).first()
		self.assertEquals(doc.id, docs[19].id)

		# descending by another_field
		doc = testdocs.list(sort=('-another_field',)).first()
		self.assertEquals(doc.id, docs[0].id)
		
		# sort has to be a list or tuple of strings
		with self.assertRaises(ParameterError):
			testdocs.list(sort='olives')
			
		with self.assertRaises(ParameterError):
			testdocs.list(sort=(17, doc))


	def test_list_filter(self):
		TestDocCollection, docs = self.generate_collection(n=20)
		testdocs = TestDocCollection()

		# simple equality filter
		results = list(testdocs.list(filter={'name': 'doc#04'}))
		self.assertEquals(len(results), 1)
		self.assertEquals(results[0].id, docs[4].id)

		# complex command
		results = list(testdocs.list(filter={'another_field': {'$lt':5}}))
		self.assertEquals(len(results), 4)


	def test_list_complex(self):
		TestDocCollection, docs = self.generate_collection(n=20)
		testdocs = TestDocCollection()

		results = list(testdocs.list(
			filter={'another_field': {'$lt':5}},
			sort=('-another_field',),
			fields=('name',),
			skip=2,
			limit=2
		))

		self.assertEquals(len(results), 2)
		self.assertEquals(results[0].id, docs[18].id)


	def test_get(self):
		TestDocCollection, docs = self.generate_collection(n=20)
		testdocs = TestDocCollection()

		doc = testdocs.get(docs[5].id)
		self.assertEquals(doc.id, docs[5].id)
		
		doc = testdocs.get(ObjectId())
		self.assertEquals(doc, None)


	def test_get_fields(self):
		TestDocCollection, docs = self.generate_collection(n=20)
		testdocs = TestDocCollection()

		doc = testdocs.get(docs[5].id, fields=('name',)).to_mongo()
		self.assertEquals(doc.get('name'), docs[5].name)
		self.assertEquals(doc.get('another_field'), None)


	def test_create(self):
		class TestDocCollection(Collection):
			document = TestDoc

		testdocs = TestDocCollection()
		
		# should fail if a field doesn't validate
		with self.assertRaises(me.ValidationError):
			doc = testdocs.create({'name':'foo', 'another_field': 'not an int'})

		doc = testdocs.create({'name':'foo', 'another_field': 123})

		# we create one and only one doc per create() and save it to the database
		num_docs = testdocs.list().count()
		self.assertEquals(num_docs, 1)

		self.assertIsInstance(doc.id, ObjectId)
		self.assertEquals(doc.name, 'foo')
		self.assertEquals(doc.another_field, 123)


	def test_update(self):
		class TestDocCollection(Collection):
			document = TestDoc

		testdocs = TestDocCollection()
		
		doc = testdocs.create({'name':'foo', 'another_field': 123})
		
		updated_doc = testdocs.update(doc.id, {'name':'bar'})
		
		self.assertEquals(updated_doc.id, doc.id)
		self.assertEquals(updated_doc.name, 'bar')
		
		# update() should return None if the specified doc doesn't exist
		result = testdocs.update(ObjectId(), {'name':'bar'})
		self.assertEquals(result, None)
		
		
	def test_delete(self):
		TestDocCollection, docs = self.generate_collection(n=20)
		testdocs = TestDocCollection()
		
		self.assertEquals(testdocs.list(limit=50).count(), 20)
		
		testdocs.delete(docs[0].id)
		
		self.assertEquals(testdocs.list(limit=50).count(), 19)
		
		
	def test_naming(self):
		class Foo(me.Document):
			pass
			
			
		class FooCollection(Collection):
			document = Foo
			
		self.assertEquals(FooCollection.singular_name, 'foo')
		self.assertEquals(FooCollection.plural_name, 'foos')
		
		class Foo2Collection(Collection):
			document = Foo
			singular_name = 'bar'
			
		self.assertEquals(Foo2Collection.singular_name, 'bar')
		self.assertEquals(Foo2Collection.plural_name, 'bars')
		
		class Foo3Collection(Collection):
			document = Foo
			plural_name = 'bazs'
			
		self.assertEquals(Foo3Collection.singular_name, 'baz')
		self.assertEquals(Foo3Collection.plural_name, 'bazs')
		
		class Foo4Collection(Collection):
			document = Foo
			singular_name = 'what the fox say'
			plural_name = 'quxes'
			
		self.assertEquals(Foo4Collection.singular_name, 'what the fox say')
		self.assertEquals(Foo4Collection.plural_name, 'quxes')
		
		class Foo5Collection(Collection):
			document = Foo
			plural_name = 'squee'
			
		self.assertEquals(Foo5Collection.singular_name, 'squee')
		self.assertEquals(Foo5Collection.plural_name, 'squee')
		
		
	def test_allowed_methods(self):
		class TestDocCollection(Collection):
			document = TestDoc
			
			def allowed_methods(self):
				return ('get',)
				
		testdocs = TestDocCollection()
		
		with self.assertRaises(NotAuthorizedError):
			testdocs.list()
			
			
	def test_enabled_methods(self):
		class TestDocCollection(Collection):
			document = TestDoc
			enabled_methods = ('list', 'get')
				
		testdocs = TestDocCollection()
		
		with self.assertRaises(NotAllowedError):
			testdocs.create({})
		
		
	def test_modify_filter(self):
		class TestDocCollection(Collection):
			document = TestDoc
			default_limit = 20
			
			def modify_filter(self, filter):
				return {'another_field':{'$gt': 5}}
		
		docs = []
		for i in range(0, 20):
			doc = TestDoc(name='doc#%02d' % i, another_field=20-i)
			doc.save()
			docs.append(doc)
		
		testdocs = TestDocCollection()
		results = testdocs.list(filter={'name':'doc#19'}, sort=('-another_field',))
		
		self.assertEquals(results.count(), 15)
		self.assertEquals(results.first().another_field, 20)
		
		
	def test_modify_filter_bad_parameter(self):
		class TestDocCollection(Collection):
			document = TestDoc
			default_limit = 20
			
			def modify_filter(self, filter):
				return 72
				
		testdocs = TestDocCollection()
		
		with self.assertRaises(ParameterError):
			results = testdocs.list(filter={})
		
		
	def test_modify_sort(self):
		class TestDocCollection(Collection):
			document = TestDoc
			
			def modify_sort(self, sort):
				return ('-name',)
		
		docs = []
		for i in range(0, 20):
			doc = TestDoc(name='doc#%02d' % i, another_field=20-i)
			doc.save()
			docs.append(doc)
		
		testdocs = TestDocCollection()
		results = testdocs.list(sort=('+name',))
		
		self.assertEquals(results.first().another_field, 1)
		
		
	def test_modify_get_fields(self):
		class TestDocCollection(Collection):
			document = TestDoc
			
			def modify_get_fields(self, fields):
				return ('name', )
		
		doc = TestDoc(name='foo', another_field=23)
		doc.save()
		
		testdocs = TestDocCollection()
		fetched_doc = testdocs.get(doc.id, fields=('another_field',)).to_mongo()
		self.assertEquals(fetched_doc.get('name'), 'foo')
		self.assertEquals(fetched_doc.get('another_field'), None)
		
		
	def test_modify_get_fields_set(self):
		class TestDocCollection(Collection):
			document = TestDoc
			
			def modify_get_fields(self, fields):
				return set(fields).intersection({'name'})
		
		doc = TestDoc(name='foo', another_field=23)
		doc.save()
		
		testdocs = TestDocCollection()
		fetched_doc = testdocs.get(doc.id, fields=('another_field','name')).to_mongo()
		self.assertEquals(fetched_doc.get('name'), 'foo')
		self.assertEquals(fetched_doc.get('another_field'), None)
		
		
	def test_modify_update_fields(self):
		class TestDocCollection(Collection):
			document = TestDoc
			
			def modify_update_fields(self, fields):
				fields['another_field'] = 5 + fields.get('another_field', 0)
				return fields
		
		testdocs = TestDocCollection()
		doc = testdocs.create({'name':'foo'})
		self.assertEquals(doc.name, 'foo')
		self.assertEquals(doc.another_field, 5)
		
		doc = testdocs.update(doc.id, {'name':'bar', 'another_field':3})
		self.assertEquals(doc.name, 'bar')
		self.assertEquals(doc.another_field, 8)
		