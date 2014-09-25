from .. import model


class JSONSchemaSerializer(object):
	
	fallbacks = (
		model.Text, model.Integer, model.Float, model.DateTime,
		model.Boolean, model.Enum, model.ListOf, model.OneOf
	)
	
	def create_schema(self, entities):
		return {
			"$schema": "http://json-schema.org/draft-04/schema#",
			"definitions": self.get_definitions(entities)
		}
		
		
	def get_definitions(self, entities):
		definitions = {}
		for e in entities:
			definitions[e.__name__] = self.get_definition(e)
		return definitions
			
			
	def get_definition(self, entity):
		props = {}
		required_props = []
		for k,v in entity.fields.items():
			props[k] = self.get_property(v)
			if v.required:
				required_props.append(k)
		definition =  {
			'properties': props
		}
		if required_props:
			definition['required'] = required_props
		return definition
			
			
	def get_property(self, field):
		prop = {}
		if field.help:
			prop['description'] = field.help
		type_name = field.__class__.__name__
		method_name = 'handle_%s' % type_name
		if not hasattr(self, method_name):
			method_name = None
			for cls in self.fallbacks:
				if isinstance(field, cls):
					method_name = 'handle_%s' % cls.__name__
					break
			if not method_name:
				raise ValueError, "No handler for %s" % type_name
		getattr(self, method_name)(field, prop)
		return prop
		
		
	def handle_Text(self, field, prop):
		prop['type'] = 'string'
		if field.maxlength:
			prop['maxLength'] = field.maxlength
		if field.minlength:
			prop['maxLength'] = field.maxlength
		if field.regex:
			prop['pattern'] = field.regex.pattern
		
		
	def handle_Integer(self, field, prop):
		prop['type'] = 'integer'
		if field.min:
			prop['minimum'] = field.min
		if field.max:
			prop['maximum'] = field.max
		
		
	def handle_Float(self, field, prop):
		prop['type'] = 'number'
		
		
	def handle_DateTime(self, field, prop):
		self.handle_Text(field, prop)
		prop['format'] = 'date-time'
		
		
	def handle_Email(self, field, prop):
		self.handle_Text(field, prop)
		prop['format'] = 'email'
		
		
	def handle_URL(self, field, prop):
		self.handle_Text(field, prop)
		prop['format'] = 'uri'
		
		
	def handle_Boolean(self, field, prop):
		prop['type'] = 'boolean'
		
		
	def handle_Enum(self, field, prop):
		prop['enum'] = field.values
		
		
	def handle_ListOf(self, field, prop):
		prop['type'] = 'array'
		prop['items'] = self.get_property(field.field)
		
		
	def handle_OneOf(self, field, prop):
		prop['oneOf'] = map(self.get_property, field.fields)
		
		
	def handle_Reference(self, field, prop):
		self.handle_Text(field, prop)
		prop['format'] = 'reference'
		prop['schema'] = '#/definitions/%s' % field.entity.__name__
		


def to_jsonschema(entities, cls=JSONSchemaSerializer):
	serializer = cls()
	return serializer.create_schema(entities)
	
	
	