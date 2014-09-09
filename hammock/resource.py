import falcon
from .methods import LIST, CREATE, GET, REPLACE, UPDATE, DELETE, get_http_methods
from .serializers import JSONSerializer, MsgPackSerializer
from .model import CompoundValidationError
from .views import View

__all__ = ['Resource']


class ResourceMeta(type):
	
	def __new__(cls, name, bases, attrs):
		singular_name = attrs.get('singular_name')
		plural_name = attrs.get('plural_name')
		entity = attrs.get('entity')
		if entity:
			entity_name = entity.__name__.lower()
		else:
			entity_name = 'unknown'
		
		if not singular_name and not plural_name:
			singular_name = entity_name
			plural_name = entity_name + 's'
		
		elif not singular_name:
			if plural_name[-1] == 's':
				singular_name = plural_name[:-1]
			else:
				singular_name = plural_name
		
		elif not plural_name:
			plural_name = singular_name + 's'
				
		
		attrs['singular_name'] = singular_name
		attrs['plural_name'] = plural_name
		
		return super(ResourceMeta, cls).__new__(cls, name, bases, attrs)


class Resource(object):
	"""
	A resource exposes an entity through HTTP
	"""
	
	__metaclass__ = ResourceMeta
	
	# The entity class that will be exposed through this resource.
	entity = None
	
	# Resources that should be used to expose the entity's references.
	#
	# This is a dictionary where the keys are the name of a reference 
	# field on the entity and the values are a resource or the name 
	# of a resource.
	reference_resources = None
	
	# A list or tuple of `hammock.methods` that are enabled through this resource.
	#
	# Note that just because a method is enabled, does not mean it will be available
	# to any request. Methods are subject to authorization rules.
	enabled_methods = ()
	
	# A list or tuple of fields that are allowed to be used in filters.
	enabled_filters = ()
	
	# A list or tuple of fields that can be used in sorting
	enabled_sort = ()
	
	# A list or tuple of fields that is a subset of `enabled_sort` that will be
	# used to sort results when no sort is supplied in the request.
	default_sort = ()
	
	# A list or tuple of authorization rules. An authorization rule is a 2-tuple. The first item is a tuple
	# of `hammock.methods` that the rule applies to. The second item is a `hammock.auth.Expression`
	authorization = ()
	
	# The types of content that are accepted
	accept_serializers = (JSONSerializer(), MsgPackSerializer())
	
	
	def __init__(self, storage, views):
		self.storage = storage
		self.views = []
		
		for v in views:
			for mimetype, _ in v.serializers:
				self.views.append((mimetype, v))
		
		
	def add_to_api(self, api):
		methods = set(self.enabled_methods)
		collection_methods = methods.intersection((LIST, CREATE))
		individual_methods = methods.intersection((GET, REPLACE, UPDATE, DELETE))
		
		if not collection_methods and not individual_methods:
			raise Exception, "%s exposes no methods" % self.__class__.__name__
		
		if collection_methods:
			api.add_route('/%s' % self.plural_name, CollectionEndpoint(self, collection_methods))
			
		if individual_methods:
			api.add_route('/%s/{id}' % self.plural_name, IndividualEndpoint(self, individual_methods))
		
		if self.reference_resources:
			for reference_name, reference in self.entity.references():
				if reference_name in self.reference_resources:
					api.add_route('/%s/{id}/%s' % (self.plural_name, reference_name), 
						ReferenceEndpoint(self, reference_name))
			
			
	def list(self, req, resp):
		return self.send_collection(req, resp, self.storage.get(self.entity))
		
		
	def create(self, req, resp):
		fields = self.get_validated_fields_from_request(req)
		id = self.storage.create(self.entity, fields)
		fields['id'] = id
		resp.status = falcon.HTTP_201
		return self.send_individual(req, resp, fields)
		
	
	def get(self, req, resp, id):
		try:
			obj = next(iter(self.storage.get(self.entity, filter={'id':id})))
		except StopIteration:
			raise falcon.HTTPNotFound
		else:
			return self.send_individual(req, resp, obj)
		
		
	def update(self, req, resp, id, replace=False):
		fields = self.get_validated_fields_from_request(req, enforce_required=replace)
		obj = self.storage.update(self.entity, id, fields, replace=replace)
		return self.send_individual(req, resp, obj)
		
		
	def replace(self, req, resp, id):
		return self.update(req, resp, id, replace=True)
		
		
	def delete(self, req, resp, id):
		self.storage.delete(self.entity, id)
		
		
	def get_reference(req, resp, id, reference_name):
		pass
		
		
	def send_collection(self, req, resp, objs):
		view = self.get_view(req)
		resp.content_type, resp.body = view.get_collection_response(req, objs)
		
		
	def send_individual(self, req, resp, obj):
		view = self.get_view(req)
		resp.content_type, resp.body = view.get_individual_response(req, obj)
		
		
	def get_validated_fields_from_request(self, req, enforce_required=True):
		fields = self.unserialize_request_body(req)
		try:
			return self.entity.validate(fields, enforce_required=enforce_required)
		except CompoundValidationError, e:
			raise falcon.HTTPBadRequest("Bad Request", "Invalid fields")
		
		
	def unserialize_request_body(self, req):
		for serializer in self.accept_serializers:
			if serializer.mimetype == req.content_type:
				return serializer.unserialize(req.stream)
		raise falcon.HTTPUnsupportedMediaType(
			'The supported types are: %s' % ', '.join([x.mimetype for x in self.accept_serializers]))
		
		
	def get_view(self, req):
		_, view = View.choose(req, self.views)
		return view
			
			
class Endpoint(object):
	
	def __init__(self, resource, methods):
		self.resource = resource
		self.register_methods(methods)
		
		
	def register_methods(self, methods):
		for method in methods:
			fn = getattr(self, method)
			for http_method in get_http_methods(method):
				setattr(self, 'on_%s' % http_method, fn)
			

class CollectionEndpoint(Endpoint):
	
	def list(self, req, resp):
		return self.resource.list(req, resp)
		
		
	def create(self, req, resp):
		return self.resource.create(req, resp)
		
		
class IndividualEndpoint(Endpoint):
	
		
	def get(self, req, resp, id):
		return self.resource.get(req, resp, id)
		
		
	def update(self, req, resp, id):
		return self.resource.update(req, resp, id)
		
	def replace(self, req, resp, id):
		return self.resource.replace(req, resp, id)
		
	def delete(self, req, resp, id):
		return self.resource.delete(req, resp, id)
		
		
class ReferenceEndpoint(object):
	
	def __init__(self, resource, reference_name):
		self.resource = resource
		self.reference_name = reference_name
		
		
	def on_get(self, req, resp, id):
		return self.get_reference(req, resp, id, reference_name)
		