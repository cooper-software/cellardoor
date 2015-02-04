from .. import model


class EntitySerializer(object):
	
	fallbacks = (
		model.Text, model.Integer, model.Float, model.DateTime,
		model.Boolean, model.Enum, model.ListOf, model.OneOf, 
		model.Compound, model.Anything
	)
		
	def create_schema(self, entity):
		props = {}
		required_props = []
		for k,v in entity.fields.items():
			props[k] = self.get_property(v)
			if v.required:
				required_props.append(k)
		definition =  {
			'title': entity.__name__,
			'properties': props,
			'links': self.get_links(entity)
		}
		if required_props:
			definition['required'] = required_props
		return definition
			
			
	def get_links(self, entity):
		if len(entity.hierarchy) > 0:
			parent = entity.hierarchy[-1]
			return {
				'parent': {
					'rel': 'parent',
					'href': '#/definitions/%s' % parent.__name__
				}
			}
		else:
			return {}
			
			
	def get_property(self, field):
		prop = {}
		prop['default'] = field.default
		prop['format'] = field.__class__.__name__
		if field.label:
			prop['title'] = field.label
		if field.description:
			prop['description'] = field.description
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
			prop['minLength'] = field.minlength
		if field.regex:
			prop['pattern'] = field.regex.pattern
		
		
	def handle_Integer(self, field, prop):
		prop['type'] = 'integer'
		if field.min:
			prop['minimum'] = field.min
		if field.max:
			prop['maximum'] = field.max
		
		
	def handle_Float(self, field, prop):
		self.handle_Integer(field, prop)
		prop['type'] = 'number'
		
		
	def handle_DateTime(self, field, prop):
		prop['type'] = 'string'
		
		
	def handle_Email(self, field, prop):
		self.handle_Text(field, prop)
		del prop['pattern']
		
		
	def handle_URL(self, field, prop):
		self.handle_Text(field, prop)
		del prop['pattern']
		
		
	def handle_Boolean(self, field, prop):
		prop['type'] = 'boolean'
		
		
	def handle_Enum(self, field, prop):
		prop['enum'] = field.values
		
		
	def handle_ListOf(self, field, prop):
		prop['type'] = 'array'
		prop['items'] = self.get_property(field.field)
		
		
	def handle_OneOf(self, field, prop):
		prop['anyOf'] = map(self.get_property, field.fields)
		
		
	def handle_Link(self, field, prop):
		self.handle_Text(field, prop)
		prop['format'] = 'Link'
		prop['schema'] = '#/definitions/%s' % field.entity.__name__
		
		
	def handle_Compound(self, field, prop):
		prop['type'] = 'object'
		properties = {}
		required = []
		for k, v in field.fields.items():
			properties[k] = self.get_property(v)
			if v.required:
				required.append(k)
		prop['properties'] = properties
		if len(required) > 0:
			prop['required'] = required
			
			
	def handle_Anything(self, field, prop):
		prop['anyOf'] = [
			{'type':'array'},
			{'type':'boolean'},
			{'type':'null'},
			{'type':'object'},
			{'type':'string'},
			{'type':'number'}
		]
			
			
	def handle_BoundingBox(self, field, prop):
		prop['type'] = 'array'
		prop['items'] = {
			'type': 'float',
			'minimum': -180.0,
			'maximum': 180.0,
			'maxItems': 4,
			'minItems': 4
		}
		
		
	def handle_LatLng(self, field, prop):
		prop['type'] = 'array'
		prop['items'] = {
			'type': 'float',
			'minimum': -180.0,
			'maximum': 180.0,
			'maxItems': 2,
			'minItems': 2
		}
		
		
	def handle_TypeOf(self, field, prop):
		type = field.types[0]
		if type == dict:
			prop['type'] = 'object'
		elif type == list:
			prop['type'] = 'array'
		elif len(field.types) == 2 and int in field.types and float in field.types:
			prop['type'] = 'number'
		elif type == int:
			prop['type'] = 'integer'
		elif type == float:
			prop['type'] = 'float'
		elif type == unicode:
			prop['type'] = 'string'
		
		
		
class APISerializer(object):
	
	def create_schema(self, api, base_url, entity_serializer):
		self.base_url = base_url
		definitions = {}
		for name, entity in api.model.entities.items():
			definitions[name] = entity_serializer.create_schema(entity)
		
		resources = {}
		for name, interface in api.interfaces.items():
			entity_links = definitions[interface.entity.__name__]['links']
			if 'resource' not in entity_links:
				entity_links['resource'] = {
					'rel': 'resource',
					'href': '#/properties/%s' % interface.plural_name
				}
			resources[interface.plural_name] = self.get_resource_schema(interface)
		
		return {
			"$schema": "http://json-schema.org/draft-04/schema#",
			"type": "object",
			"definitions": definitions,
			"properties": resources
		}
		
		
	def get_resource_schema(self, interface):
		links = {}
		
		for method in interface.rules.enabled_methods:
			fn = getattr(self, 'get_%s_link' % method)
			links[method] = fn(interface)
			
		for k,v in interface.entity.links.items():
			links['link-%s' % k] = self.get_link_link(interface, k, v)
		
		return {
			"title": interface.plural_name,
			"links": links
		}
		
		
	def get_list_link(self, interface):
		return {
			'href': self.base_url + '/%s' % interface.plural_name,
			'method': 'GET',
			'rel': 'instances',
			'title': 'List',
			'targetSchema': {
				'type': 'array',
				'items': {
					'$ref': self.entity_schema_ref(interface)
				}
			}
		}
		
		
	def get_get_link(self, interface):
		return {
			'href': self.base_url + '/%s/{id}' % interface.plural_name,
			'method': 'GET',
			'rel': 'instance',
			'title': 'Details',
			'targetSchema': { '$ref': self.entity_schema_ref(interface) }
		}
		
		
	def get_create_link(self, interface):
		return {
			'href': self.base_url + '/%s' % interface.plural_name,
			'method': 'POST',
			'rel': 'create',
			'title': 'New',
			'schema': { '$ref': self.entity_schema_ref(interface) },
			'targetSchema': { '$ref': self.entity_schema_ref(interface) }
		}
		
		
	def get_update_link(self, interface):
		return {
			'href': self.base_url + '/%s/{id}' % interface.plural_name,
			'method': 'PATCH',
			'rel': 'update',
			'title': 'Update',
			'schema': {
				'allOf': [ { '$ref': self.entity_schema_ref(interface) } ],
				'required': []
			},
			'targetSchema': { '$ref': self.entity_schema_ref(interface) }
		}
		
		
	def get_replace_link(self, interface):
		return {
			'href': self.base_url + '/%s/{id}' % interface.plural_name,
			'method': 'PUT',
			'rel': 'replace',
			'title': 'Replace',
			'schema': { '$ref': self.entity_schema_ref(interface) },
			'targetSchema': { '$ref': self.entity_schema_ref(interface) }
		}
		
		
	def get_delete_link(self, interface):
		return {
			'href': self.base_url + '/%s/{id}' % interface.plural_name,
			'method': 'DELETE',
			'rel': 'delete',
			'title': 'Delete'
		}
		
		
	def get_link_link(self, interface, link_name, link_interface):
		schema_link = {
			'href': self.base_url + '/%s/{id}/%s' % (interface.plural_name, link_name),
			'method': 'GET',
			'rel': 'link',
			'title': 'Link'
		}
		
		link = None
		entities = [interface.entity] + interface.entity.children
		for entity in entities:
			link = entity.fields.get(link_name)
			if not link:
				link = entity.links.get(link_name)
			if link:
				break
		
		if interface.entity.is_multiple_link(link):
			schema_link['targetSchema'] = {
				'type': 'array',
				'items': { '$ref': self.entity_schema_ref(link_interface) }
			}
		else:
			schema_link['targetSchema'] = { '$ref': self.entity_schema_ref(link_interface) }
			
		return schema_link
		
		
	def entity_schema_ref(self, interface):
		return '#/definitions/%s' % interface.entity.__name__


def to_jsonschema(api, base_url, api_cls=APISerializer, entity_cls=EntitySerializer):
	api_serializer = api_cls()
	entity_serializer = entity_cls()
	return api_serializer.create_schema(api, base_url, entity_serializer)
	
	
	