import unittest
import re
from mock import Mock
from cellardoor.spec import jsonschema
from cellardoor.model import *
from cellardoor.api import API, Interface
from cellardoor.api.methods import ALL

model = Model()

class Bar(model.Entity):
	pass

class Foo(model.Entity):
    a = Compound(foo=Text())
    b = Text(required=True, minlength=100, maxlength=5000, regex=re.compile('^b'))
    c = HTML(label="Some stuff")
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
		
		
	def test_label(self):
		class Foo(self.model.Entity):
			stuff = Integer(label="Blah blah blah")
			
		schema = self.get_schema(Foo)
		self.assertEquals(schema['properties']['stuff']['title'], 'Blah blah blah')
		
		
	def test_description(self):
		class Foo(self.model.Entity):
			stuff = Integer(description="Blah blah blah")
			
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
			things = Text(minlength=100, maxlength=5000, regex=re.compile('^b'))
			
		schema = self.get_schema(Foo)
		self.assertEquals(
			schema['properties']['stuff'], 
			{
				'default': None, 
				'format': 'Text', 
				'type': 'string'
			}
		)
		self.assertEquals(
			schema['properties']['things'], 
			{
				'default': None, 
				'format': 'Text', 
				'type': 'string',
				'minLength': 100,
				'maxLength': 5000,
				'pattern': '^b'
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
	
	maxDiff = None
	
	def get_schema(self, api, entity_serializer=None):
		if entity_serializer is None:
			entity_serializer = jsonschema.EntitySerializer()
		serializer = jsonschema.APISerializer()
		return serializer.create_schema(api, 'http://www.example.com/api', entity_serializer)
		
	
	def test_empty(self):
		schema = self.get_schema(API(Model()))
		self.assertEquals(
			schema,
			{
				'$schema': 'http://json-schema.org/draft-04/schema#',
				'type': 'object',
				'definitions': {},
				'properties': {}
			}
		)
		
		
	def test_entity(self):
		entity_serializer = Mock()
		entity_serializer.create_schema = Mock(return_value='foo')
		
		model = Model()
		class Foo(model.Entity):
			pass
			
		api = API(model)
		schema = self.get_schema(api, entity_serializer)
		
		entity_serializer.create_schema.assert_called_once_with(Foo)
		
		self.assertEquals(
			schema['definitions'],
			{ 'Foo': 'foo' }
		)
		
		
	def test_interface(self):
		model = Model(storage=Mock())
		class Foo(model.Entity):
			pass
			
		api = API(model)
		
		class Foos(api.Interface):
			entity = Foo
			
		
		schema = self.get_schema(api)
		self.assertEquals(
			schema['definitions']['Foo'],
			{
				'title': 'Foo',
				'properties':{},
				'links': {
					'resource': {
						'rel': 'resource',
						'href': '#/properties/foos'
					}
				}
			}
		)
		self.assertEquals(
			schema['properties']['foos'],
			{
				'title': 'foos',
				'links': {}
			}
		)
		
		
	def test_methods(self):
		model = Model(storage=Mock())
		class Foo(model.Entity):
			pass
			
		api = API(model)
		
		class Foos(api.Interface):
			entity = Foo
			method_authorization = {
				ALL: None
			}
			
		
		schema = self.get_schema(api)
		self.assertEquals(
			schema['properties']['foos']['links']['create'],
			{
				'href': 'http://www.example.com/api/foos',
                'method': 'POST',
                'rel': 'create',
                'schema': {'$ref': '#/definitions/Foo'},
                'targetSchema': {'$ref': '#/definitions/Foo'},
                'title': 'New'
            }
		)
		self.assertEquals(
			schema['properties']['foos']['links']['delete'],
			{
				'href': 'http://www.example.com/api/foos/{id}',
                'method': 'DELETE',
                'rel': 'delete',
                'title': 'Delete'
            }
		)
		self.assertEquals(
			schema['properties']['foos']['links']['get'],
			{
				'href': 'http://www.example.com/api/foos/{id}',
                'method': 'GET',
                'rel': 'instance',
                'targetSchema': {'$ref': '#/definitions/Foo'},
                'title': 'Details'
            }
		)
		self.assertEquals(
			schema['properties']['foos']['links']['list'],
			{
				'href': 'http://www.example.com/api/foos',
                'method': 'GET',
                'rel': 'instances',
                'targetSchema':
                {
                	'type': 'array',
                	'items': {'$ref': '#/definitions/Foo'}
                },
                'title': 'List'
            }
		)
		self.assertEquals(
			schema['properties']['foos']['links']['replace'],
			{
				'href': 'http://www.example.com/api/foos/{id}',
                'method': 'PUT',
                'rel': 'replace',
                'schema': {'$ref': '#/definitions/Foo'},
                'targetSchema': {'$ref': '#/definitions/Foo'},
                'title': 'Replace'
            }
		)
		self.assertEquals(
			schema['properties']['foos']['links']['update'],
			{
				'href': 'http://www.example.com/api/foos/{id}',
                'method': 'PATCH',
                'rel': 'update',
                'schema':
                {
                	'allOf': [
                		{'$ref': '#/definitions/Foo'}
            		],
                    'required': []
                },
                'targetSchema': {'$ref': '#/definitions/Foo'},
                'title': 'Update'
            }
		)
		
		
	def test_entity_links(self):
		model = Model(storage=Mock())
		
		class Foo(model.Entity):
			pass
			
		class Bar(model.Entity):
			foos = ListOf(Link(Foo))
			foo = Link(Foo)
			baz = Link('Baz')
			
		class Baz(model.Entity):
			bars = InverseLink(Bar, 'baz')
			
		api = API(model)
		
		class Bars(api.Interface):
			entity = Bar
			
		class Bazes(api.Interface):
			entity = Baz
			plural_name = 'bazes'
			
		schema = self.get_schema(api)
		self.assertEquals(
			schema['properties']['bars']['links']['link-foos'],
			{
				'href': 'http://www.example.com/api/bars/{id}/foos',
				'method': 'GET',
				'rel': 'link',
				'targetSchema': 
				{
					'type': 'array',
					'items': {'$ref': '#/definitions/Foo'}
                },
				'title': 'Link'
			}
		)
		self.assertEquals(
			schema['properties']['bars']['links']['link-foo'],
			{
				'href': 'http://www.example.com/api/bars/{id}/foo',
				'method': 'GET',
				'rel': 'link',
				'targetSchema': {'$ref': '#/definitions/Foo'},
				'title': 'Link'
			}
		)
		self.assertEquals(
			schema['properties']['bars']['links']['link-baz'],
			{
				'href': 'http://www.example.com/api/bars/{id}/baz',
				'method': 'GET',
				'rel': 'link',
				'targetSchema': {'$ref': '#/definitions/Baz'},
				'title': 'Link'
			}
		)
		self.assertEquals(
			schema['properties']['bazes']['links']['link-bars'],
			{
				'href': 'http://www.example.com/api/bazes/{id}/bars',
				'method': 'GET',
				'rel': 'link',
				'targetSchema':
				{
					'type': 'array',
					'items': {'$ref': '#/definitions/Bar'}
                },
				'title': 'Link'
			}
		)
		
		
class TestJSONSchema(unittest.TestCase):
	
	def test_jsonschema(self):
		model = Model(storage=Mock())
		
		class Foo(model.Entity):
			pass
			
		api = API(model)
		
		class Foos(api.Interface):
			entity = Foo
		
		schema = jsonschema.to_jsonschema(api, 'http://www.example.com/api')
		self.assertEquals(
			schema,
			{
				'$schema': 'http://json-schema.org/draft-04/schema#',
				'type': 'object',
				'definitions': 
				{
					'Foo': 
					{
						'title': 'Foo',
						'properties':{},
						'links': {
							'resource': {
								'rel': 'resource',
								'href': '#/properties/foos'
							}
						}
					}
				},
				'properties':
				{
					'foos':
					{
						'title': 'foos',
						'links': {}
					}
				}
			}
		)