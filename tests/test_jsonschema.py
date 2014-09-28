import unittest
import re
from cellardoor.spec import jsonschema
from cellardoor.model import *

class Bar(Entity):
	pass

class Foo(Entity):
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
    p = Reference(Bar)
    q = Link(Bar, 'a')

field_schema = {
	'a': {
		'type': 'object',
		'properties': {
			'foo': {
				'type': 'string',
				'default': None
			}
		},
		'default': None
	},
	'b': {
		'type': 'string',
		'minLength': 100,
		'maxLength': 5000,
		'pattern': '^b',
		'default': None
	},
	'c': {
		'type': 'string',
		'description': 'Some stuff',
		'format': 'html',
		'default': None
	},
	'd': {
		'type': 'string',
		'format': 'email',
		'default': None
	},
	'e': {
		'type': 'string',
		'format': 'date-time',
		'default': None
	},
	'f': {
		'type': 'boolean',
		'default': None
	},
	'g': {
		'type': 'number',
		'minimum': 5.331,
		'maximum': 7.2,
		'default': None
	},
	'h': {
		'type': 'integer',
		'default': None
	},
	'i': {
		'type': 'array',
		'items': {
			'type': 'float',
			'minimum': -180.0,
			'maximum': 180.0,
			'maxItems': 4,
			'minItems': 4
		},
		'default': None
	},
	'j': {
		'type': 'array',
		'items': {
			'type': 'float',
			'minimum': -180.0,
			'maximum': 180.0,
			'maxItems': 2,
			'minItems': 2
		},
		'default': None
	},
	'k': {
		'enum': ('a', 'b', 'c'),
		'default': 'c'
	},
	'm': {
		'type': 'string',
		'format': 'uri',
		'default': None
	},
	'n': {
		'anyOf': [
			{
				'type': 'integer',
				'default': None
			},
			{
				'type': 'number',
				'default': None
			}
		],
		'default': None
	},
	'o': {
		'type': 'array',
		'items': {
			'type': 'string',
			'default': None
		},
		'default': []
	},
	'p': {
		'type': 'string',
		'format': 'reference',
		'schema': '#/definitions/Bar',
		'default': None
	}
}

class TestJSONSchema(unittest.TestCase):
	
	maxDiff = None
	
	def test_entity_serializer(self):
		serializer = jsonschema.EntitySerializer()
		schema = serializer.create_schema(Foo)
		
		self.assertEquals(schema['required'], ['b', 'd'])
		
		for k,v in field_schema.items():
			self.assertEquals(schema['properties'][k], v)
		