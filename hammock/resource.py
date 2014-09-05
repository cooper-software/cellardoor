from .methods import LIST, CREATE, GET, UPDATE, DELETE, get_http_methods

__all__ = ['Resource']


class ResourceMeta(type):
	
	def __new__(cls, name, bases, dict):
		singular_name = dict.get('singular_name')
		plural_name = dict.get('plural_name')
		document = dict.get('document')
		if document:
			document_name = document.__name__.lower()
		else:
			document_name = 'unknown'
		
		if not singular_name and not plural_name:
			singular_name = document_name
			plural_name = document_name + 's'
		
		elif not singular_name:
			if plural_name[-1] == 's':
				singular_name = plural_name[:-1]
			else:
				singular_name = plural_name
		
		elif not plural_name:
			plural_name = singular_name + 's'
				
		
		dict['singular_name'] = singular_name
		dict['plural_name'] = plural_name
		
		return super(ResourceMeta, cls).__new__(cls, name, bases, dict)


class Resource(object):
	"""
	A resource exposes a model through HTTP
	"""
	
	__metaclass__ = ResourceMeta
	
	# The model class that will be exposed through this resource.
	model = None
	
	# Resources that should be used to expose the model's references.
	#
	# This is a dictionary where the keys are the name of a reference 
	# field on the model and the values are a resource or the name 
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
	default_sort = ())
	
	# A list or tuple of authorization rules. An authorization rule is a 2-tuple. The first item is a tuple
	# of `hammock.methods` that the rule applies to. The second item is a `hammock.auth.Expression`
	authorization = ()
	
	
	def __init__(self, storage, views):
		self.storage = storage
		self.views = views
		
		
	def add_to_api(self, api):
		methods = set(self.enabled_methods)
		collection_methods = methods.intersection((LIST, CREATE))
		individual_methods = methods.intersection((GET, UPDATE, DELETE))
		
		api.add_route('/%s' % self.plural_name, CollectionEndpoint(self, collection_methods))
		api.add_route('/%s/{%s_id}' % (self.plural_name, self.singular_name), IndividualEndpoint(self, individual_methods))
		
		for reference_name, reference in self.model.references():
			if reference_name in self.reference_resources
				api.add_route('/%s/{%s_id}/%s' % (self.plural_name, self.singular_name, reference_name), 
					ReferenceEndpoint(self, reference_name))
			
			
	def list(self, req, resp):
		return self.respond(req, resp, self.storage.get(self.model))
		
		
	def create(self, req, resp):
		fields = self.parse_request_body(req)
	
	
	def get(self, req, resp, id):
		pass
		
		
	def update(self, req, resp, id):
		pass
		
		
	def delete(self, req, resp, id):
		pass
	
	
	def get_reference(req, resp, id, reference_name):
		pass
		
	def respond(self, req, resp, result):
		pass
			
			
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
		
		
	def delete(self, req, resp, id):
		return self.resource.delete(req, resp, id)
		
		
class ReferenceEndpoint(object):
	
	def __init__(self, resource, reference_name):
		self.resource = resource
		self.reference_resource = reference_resource
		
		
	def on_get(self, req, resp, id):
		return self.get_reference(req, resp, id, reference_name)
		