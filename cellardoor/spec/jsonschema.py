from .. import model


class EntitySerializer(object):
	
	fallbacks = (
		model.Text, model.Integer, model.Float, model.DateTime,
		model.Boolean, model.Enum, model.ListOf, model.OneOf
	)
		
	def create_schema(self, entity):
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
		prop['default'] = field.default
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
		
		
		
class APISerializer(object):
	
	def create_schema(self, api, base_url, entity_serializer):
		self.base_url = base_url
		definitions = {}
		for e in api.entities:
			definitions[e.__name__] = entity_serializer.create_schema(e)
		
		resources = {}
		for collection in api.collections:
			resources[collection.plural_name] = self.get_resource_schema(collection)
		
		return {
			"$schema": "http://json-schema.org/draft-04/schema#",
			"type": "object",
			"definitions": definitions,
			"properties": resources
		}
		
		
	def get_resource_schema(self, collection):
		links = {}
		
		for method in collection.rules.enabled_methods:
			fn = getattr(self, 'get_%s_link' % method)
			links[method] = fn(collection)
		
		return {
			"links": links
		}
		
		
	def get_list_link(self, collection):
		return {
			'href': self.base_url + '/%s' % collection.plural_name,
			'method': 'GET',
			'rel': 'instances',
			'title': 'List',
			'targetSchema': {
				'type': 'array',
				'items': {
					'$ref': self.entity_schema_ref(collection)
				}
			}
		}
		
		
	def get_get_link(self, collection):
		return {
			'href': self.base_url + '/%s/{id}' % collection.plural_name,
			'method': 'GET',
			'rel': 'instance',
			'title': 'Details',
			'targetSchema': { '$ref': self.entity_schema_ref(collection) }
		}
		
		
	def get_create_link(self, collection):
		return {
			'href': self.base_url + '/%s' % collection.plural_name,
			'method': 'POST',
			'rel': 'create',
			'title': 'New',
			'schema': { '$ref': self.entity_schema_ref(collection) },
			'targetSchema': { '$ref': self.entity_schema_ref(collection) }
		}
		
		
	def get_update_link(self, collection):
		return {
			'href': self.base_url + '/%s/{id}' % collection.plural_name,
			'method': 'PATCH',
			'rel': 'update',
			'title': 'Update',
			'schema': {
				'allOf': [ { '$ref': self.entity_schema_ref(collection) } ],
				'required': []
			},
			'targetSchema': { '$ref': self.entity_schema_ref(collection) }
		}
		
		
	def get_replace_link(self, collection):
		return {
			'href': self.base_url + '/%s/{id}' % collection.plural_name,
			'method': 'PUT',
			'rel': 'replace',
			'title': 'Replace',
			'schema': { '$ref': self.entity_schema_ref(collection) },
			'targetSchema': { '$ref': self.entity_schema_ref(collection) }
		}
		
		
	def get_delete_link(self, collection):
		return {
			'href': self.base_url + '/%s/{id}' % collection.plural_name,
			'method': 'DELETE',
			'rel': 'delete',
			'title': 'Delete'
		}
		
		
	def entity_schema_ref(self, collection):
		return '#/definitions/%s' % collection.entity.__class__.__name__


def to_jsonschema(api, base_url, api_cls=APISerializer, entity_cls=EntitySerializer):
	api_serializer = api_cls()
	entity_serializer = entity_cls()
	return api_serializer.create_schema(api, base_url, entity_serializer)
	
	
	