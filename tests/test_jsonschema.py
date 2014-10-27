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

field_schema = {
	'a': {
		'type': 'object',
		'properties': {
			'foo': {
				'type': 'string',
				'default': None,
				'format': 'Text'
			}
		},
		'default': None,
		'format': 'Compound'
	},
	'b': {
		'type': 'string',
		'minLength': 100,
		'maxLength': 5000,
		'pattern': '^b',
		'default': None,
		'format': 'Text'
	},
	'c': {
		'type': 'string',
		'description': 'Some stuff',
		'format': 'html',
		'default': None,
		'format': 'HTML'
	},
	'd': {
		'type': 'string',
		'format': 'email',
		'default': None,
		'format': 'Email'
	},
	'e': {
		'type': 'string',
		'format': 'date-time',
		'default': None,
		'format': 'DateTime'
	},
	'f': {
		'type': 'boolean',
		'default': None,
		'format': 'Boolean'
	},
	'g': {
		'type': 'number',
		'minimum': 5.331,
		'maximum': 7.2,
		'default': None,
		'format': 'Float'
	},
	'h': {
		'type': 'integer',
		'default': None,
		'format': 'Integer'
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
		'default': None,
		'format': 'BoundingBox'
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
		'default': None,
		'format': 'LatLng'
	},
	'k': {
		'enum': tuple(set(('a', 'b', 'c'))),
		'default': 'c',
		'format': 'Enum'
	},
	'm': {
		'type': 'string',
		'format': 'uri',
		'default': None,
		'format': 'URL'
	},
	'n': {
		'anyOf': [
			{
				'type': 'integer',
				'default': None,
				'format': 'Integer'
			},
			{
				'type': 'number',
				'default': None,
				'format': 'Float'
			}
		],
		'default': None,
		'format': 'OneOf'
	},
	'o': {
		'type': 'array',
		'items': {
			'type': 'string',
			'default': None,
			'format': 'Text'
		},
		'default': [],
		'format': 'ListOf'
	},
	'p': {
		'type': 'string',
		'format': 'Link',
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
		