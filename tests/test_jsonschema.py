import unittest
import re
from cellardoor.spec import jsonschema
from cellardoor.model import *

model = Model()

class Bar(model.Entity):
	pass

class Foo(model.Entity):
    a = Compound(foo=Text())
    b = Text(required=True, minlength=100, maxlength=5000, regex=re.compile('^b'))
    c = HTML(help="Some stuff")
    d = Email(required=True)
    e = DateTime()
    f = Boolean()
    g = Float(min=5.331, max=7.2)
    h = Integer()
    i = BoundingBox()
    j = LatLng()
    k = Enum('a', 'b', 'c', default='c')
    m = URL()
    n = OneOf(Integer(), Float())
    o = ListOf(Text())
    p = Link(Bar)
    q = InverseLink(Bar, 'a')

class TestEntitySerializer(unittest.TestCase):
	
	maxDiff = None
	
	def setUp(self):
		self.entity_serializer = jsonschema.EntitySerializer()
		self.model = Model()
		
	def get_schema(self, entity):
		return self.entity_serializer.create_schema(entity)
	
	def test_base_properties(self):
		"""
		Should conform to minimum JSON Schema standard
		"""
		class Foo(self.model.Entity):
			pass
			
		schema = self.entity_serializer.create_schema(Foo)
		self.assertEquals(schema.get('properties'), {})
		self.assertEquals(schema.get('links'), {})
		self.assertEquals(schema.get('title'), 'Foo')
		
		
	def test_required(self):
		class Foo(self.model.Entity):
			stuff = Integer(required=True)
			things = ListOf(Text(), required=True)
			metasyntacticvariable = Float()
			
		schema = self.get_schema(Foo)
		self.assertEquals(schema['required'], ['things', 'stuff'])
		
		
	def test_help(self):
		class Foo(self.model.Entity):
			stuff = Integer(help="Blah blah blah")
			
		schema = self.get_schema(Foo)
		self.assertEquals(schema['properties']['stuff']['description'], 'Blah blah blah')
		
		
	def test_default(self):
		class Foo(self.model.Entity):
			stuff = Integer(default="whale")
			
		schema = self.get_schema(Foo)
		self.assertEquals(schema['properties']['stuff']['default'], 'whale')
		
		
	def test_fallback(self):
		class Thingy(Text):
			pass
			
		class Foo(self.model.Entity):
			stuff = Thingy()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None,
				'format': 'Thingy',
				'type': 'string'
			}
		)
		
		
	def test_fallback_fail(self):
		class Thingy(Field):
			pass
			
		class Foo(self.model.Entity):
			stuff = Thingy()
		
		with self.assertRaises(Exception):
			self.get_schema(Foo)
			
			
	def test_inheritance(self):
		class Foo(self.model.Entity):
			pass
			
		class Bar(Foo):
			pass
			
		schema = self.get_schema(Bar)
		self.assertEquals(
			schema['links'],
			{
				'parent': 
				{
					'href': '#/definitions/Foo',
					'rel': 'parent'
				}
			}
		)
		
		
	def test_Compound(self):
		class Foo(self.model.Entity):
			stuff = Compound(foo=Text(), bar=Text(required=True))
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'],
			{
				'default': None,
				'format': 'Compound',
				'type': 'object',
				'required': ['bar'],
				'properties': {
					'foo': {
						'default': None,
						'format': 'Text',
						'type': 'string'
					},
					'bar': {
						'default': None,
						'format': 'Text',
						'type': 'string'
					}
				}
			}
		)
	
	
	def test_Text(self):
		class Foo(self.model.Entity):
			stuff = Text()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'Text', 
				'type': 'string'
			}
		)
		
		
	def test_HTML(self):
		class Foo(self.model.Entity):
			stuff = HTML()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'HTML', 
				'type': 'string'
			}
		)
		
		
	def test_Email(self):
		class Foo(self.model.Entity):
			stuff = Email()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'Email', 
				'type': 'string'
			}
		)
		
	def test_DateTime(self):
		class Foo(self.model.Entity):
			stuff = DateTime()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'DateTime', 
				'type': 'string'
			}
		)
		
		
	def test_Boolean(self):
		class Foo(self.model.Entity):
			stuff = Boolean()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'Boolean', 
				'type': 'boolean'
			}
		)
		
		
	def test_Float(self):
		class Foo(self.model.Entity):
			stuff = Float()
			things = Float(min=5.331, max=7.2)
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'Float', 
				'type': 'number'
			}
		)
		self.assertEquals(
			schema['properties']['things'], 
			{
				'default': None, 
				'format': 'Float', 
				'type': 'number',
				'maximum': 7.2,
				'minimum': 5.331
			}
		)
		
		
	def test_Integer(self):
		class Foo(self.model.Entity):
			stuff = Integer()
			things = Integer(min=5, max=7)
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'Integer', 
				'type': 'integer'
			}
		)
		self.assertEquals(
			schema['properties']['things'], 
			{
				'default': None, 
				'format': 'Integer', 
				'type': 'integer',
				'maximum': 7,
				'minimum': 5
			}
		)
		
		
	def test_BoundingBox(self):
		class Foo(self.model.Entity):
			stuff = BoundingBox()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'BoundingBox', 
				'type': 'array',
				'items': {
					'maxItems': 4,
					'minItems': 4,
					'minimum': -180.0,
					'maximum': 180.0,
					'type': 'float'
				}
			}
		)
		
		
	def test_LatLng(self):
		class Foo(self.model.Entity):
			stuff = LatLng()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'LatLng', 
				'type': 'array',
				'items': {
					'maxItems': 2,
					'minItems': 2,
					'minimum': -180.0,
					'maximum': 180.0,
					'type': 'float'
				}
			}
		)
		
		
	def test_Enum(self):
		class Foo(self.model.Entity):
			stuff = Enum('a', 'b', 'c')
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'Enum', 
				'enum': set(['a', 'b', 'c'])
			}
		)
		
		
	def test_URL(self):
		class Foo(self.model.Entity):
			stuff = URL()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'URL', 
				'type': 'string'
			}
		)
		
		
	def test_OneOf(self):
		class Foo(self.model.Entity):
			stuff = OneOf(Integer(), Float())
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'OneOf', 
				'anyOf': [
					{
						'default': None,
						'format': 'Integer',
						'type': 'integer'
					},
					{
						'default': None,
						'format': 'Float',
						'type': 'number'
					}
				]
			}
		)
		
		
	def test_ListOf(self):
		class Foo(self.model.Entity):
			stuff = ListOf(Text())
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': [], 
				'format': 'ListOf', 
				'type': 'array',
				'items': {
					'default': None,
					'format': 'Text',
					'type': 'string'
				}
			}
		)
		
		
	def test_TypeOf(self):
		class Foo(self.model.Entity):
			foo = TypeOf(dict)
			bar = TypeOf(list)
			baz = TypeOf(int)
			qux = TypeOf(float)
			fred = TypeOf(unicode)
			wibble = TypeOf(int, float)
			wobble = TypeOf(TypeOf)
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties'], 
			{
				'foo': {
					'default': None,
					'format': 'TypeOf',
					'type': 'object'
				},
				'bar': {
					'default': None,
					'format': 'TypeOf',
					'type': 'array'
				},
				'baz': {
					'default': None,
					'format': 'TypeOf',
					'type': 'integer'
				},
				'qux': {
					'default': None,
					'format': 'TypeOf',
					'type': 'float'
				},
				'fred': {
					'default': None,
					'format': 'TypeOf',
					'type': 'string'
				},
				'wibble': {
					'default': None,
					'format': 'TypeOf',
					'type': 'number'
				},
				'wobble': {
					'default': None,
					'format': 'TypeOf'
				}
			}
		)
		
	def test_Anything(self):
		class Foo(self.model.Entity):
			stuff = Anything()
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None,
				'format': 'Anything',
				'anyOf': [
					{'type':'array'},
					{'type':'boolean'},
					{'type':'null'},
					{'type':'object'},
					{'type':'string'},
					{'type':'number'}
				]
			}
		)
		
		
	def test_Link(self):
		class Foo(self.model.Entity):
			stuff = Link(Bar)
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None,
				'format': 'Link',
				'type': 'string',
				'schema': '#/definitions/Bar'
			}
		)
		
		
	def test_InverseLink(self):
		class Foo(self.model.Entity):
			stuff = InverseLink(Bar, 'a')
			
		schema = self.get_schema(Foo)
		self.assertEquals(schema['properties'].get('stuff'), None)
	
	
class TestAPISerializer(unittest.TestCase):
	pass