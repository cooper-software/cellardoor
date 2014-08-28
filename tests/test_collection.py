import unittest
import mongoengine as me
from hammock import Collection

class TestDoc(me.Document):
	name = me.StringField()
	another_field = me.IntField()


me.connect('hammock_test')


class TestCollection(unittest.TestCase):

	def setUp(self):
		TestDoc.objects().delete()


	def test_identity(self):
		class TestDocs(Collection):
			document = TestDoc

		identity = {'foo':'bar'}
		testdocs = TestDocs(identity)
		self.assertEquals(testdocs.identity, identity)


	def test_list_limits_and_skip(self):
		for i in range(0, 20):
			doc = TestDoc(name='doc#%d' % i)
			doc.save()

		self.assertEquals(TestDoc.objects().count(), 20)

		class TestDocs(Collection):
			document = TestDoc
			default_limit = 10
			max_limit = 15

		testdocs = TestDocs()

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
		self.assertEquals(results[0].name, 'doc#3')


	def test_list_fields(self):
		TestDoc(name='foo', another_field=23).save()
		
		class TestDocs(Collection):
			document = TestDoc

		testdocs = TestDocs()

		# include_fields exclusively includes the listed fields
		doc = testdocs.list(include_fields=('name',)).first().to_mongo()
		self.assertEquals(doc.get('name'), 'foo')
		self.assertEquals(doc.get('another_field'), None)

		# exclude fields excludes only the listed fields
		doc = testdocs.list(exclude_fields=('name',)).first().to_mongo()
		self.assertEquals(doc.get('name'), None)
		self.assertEquals(doc.get('another_field'), 23)

		# exclude overrides include
		doc = testdocs.list(include_fields=('name',), exclude_fields=('name',)).first().to_mongo()
		self.assertEquals(doc.get('name'), None)
		self.assertEquals(doc.get('another_field'), 23)		


	def test_list_sort(self):
		docs = []
		for i in range(0, 20):
			doc = TestDoc(name='doc#%02d' % i, another_field=20-i)
			doc.save()
			docs.append(doc)

		class TestDocs(Collection):
			document = TestDoc

		testdocs = TestDocs()

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


	def test_list_filter(self):
		docs = []
		for i in range(0, 20):
			doc = TestDoc(name='doc#%02d' % i, another_field=20-i)
			doc.save()
			docs.append(doc)

		class TestDocs(Collection):
			document = TestDoc

		testdocs = TestDocs()

		# simple equality filter
		results = list(testdocs.list(filter={'name': 'doc#04'}))
		self.assertEquals(len(results), 1)
		self.assertEquals(results[0].id, docs[4].id)

		# complex command
		results = list(testdocs.list(filter={'another_field': {'$lt':5}}))
		self.assertEquals(len(results), 4)


	def test_list_complex(self):
		docs = []
		for i in range(0, 20):
			doc = TestDoc(name='doc#%02d' % i, another_field=20-i)
			doc.save()
			docs.append(doc)

		class TestDocs(Collection):
			document = TestDoc

		testdocs = TestDocs()

		results = list(testdocs.list(
			filter={'another_field': {'$lt':5}},
			sort=('-another_field',),
			include_fields=('name',),
			skip=2,
			limit=2
		))

		self.assertEquals(len(results), 2)
		self.assertEquals(results[0].id, docs[18].id)


	def test_get(self):
		pass