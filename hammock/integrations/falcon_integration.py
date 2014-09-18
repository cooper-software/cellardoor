import functools
import falcon
import json
import logging
from ..methods import LIST, CREATE, GET, REPLACE, UPDATE, DELETE, get_http_methods
from ..serializers import JSONSerializer, MsgPackSerializer
from ..views import View
from .. import errors

__all__ = ['add_to_falcon']


class Resource(object):
	"""
	A resource exposes a collection through falcon
	"""
	
	# The types of content that are accepted.
	accept_serializers = (JSONSerializer(), MsgPackSerializer())
	
	
	def __init__(self, collection, views):
		self.collection = collection
		self.views = views
		self.logger = logging.getLogger(__name__)
		
		
	def add_to_falcon(self, app):
		methods = set(self.collection.enabled_methods)
		collection_methods = methods.intersection((LIST, CREATE))
		individual_methods = methods.intersection((GET, REPLACE, UPDATE, DELETE))
		
		if not collection_methods and not individual_methods:
			raise Exception, "The '%s' collection exposes no methods" % self.collection.plural_name
		
		if collection_methods:
			app.add_route('/%s' % self.collection.plural_name, ListEndpoint(self, collection_methods))
			
		if individual_methods:
			app.add_route('/%s/{id}' % self.collection.plural_name, IndividualEndpoint(self, individual_methods))
		
		if self.collection.links:
			for reference_name, reference in self.collection.entity.links_and_references:
				if reference_name in self.collection.links:
					app.add_route('/%s/{id}/%s' % (self.collection.plural_name, reference_name), 
						ReferenceEndpoint(self, reference_name))
			
	
	def list(self, req, resp):
		filter, sort, offset, limit, show_hidden = self.get_list_params(req)
		items = self.collection.list(filter=filter, sort=sort, offset=offset, limit=limit, show_hidden=show_hidden)
		self.send_list(req, resp, items)
		
		
	def create(self, req, resp):
		fields = self.get_fields_from_request(req)
		item = self.collection.create(fields, show_hidden=self.get_show_hidden(req))
		resp.status = falcon.HTTP_201
		self.send_one(req, resp, item)
		
	
	def get(self, req, resp, id):
		item = self.collection.get(id, show_hidden=self.get_show_hidden(req))
		self.send_one(req, resp, item)
		
		
	def update(self, req, resp, id):
		fields = self.get_fields_from_request(req)
		item = self.collection.update(id, fields, show_hidden=self.get_show_hidden(req))
		self.send_one(req, resp, item)
		
		
	def replace(self, req, resp, id):
		fields = self.get_fields_from_request(req)
		item = self.collection.replace(id, fields, show_hidden=self.get_show_hidden(req))
		self.send_one(req, resp, item)
		
		
	def delete(self, req, resp, id):
		self.collection.delete(id)
		
		
	def get_link_or_reference(self, req, resp, id, reference_name):
		filter, sort, offset, limit, show_hidden = self.get_list_params(req)
		result = self.collection.link(id, reference_name, filter=filter, sort=sort, offset=offset, limit=limit, show_hidden=show_hidden)
		if isinstance(result, dict):
			self.send_one(req, resp, result)
		else:
			self.send_list(req, resp, result)
		
		
	def call_collection(self, req, resp, method_name, *args, **kwargs):
		return getattr(self.collection, method_name)(*args, **kwargs)
		
		
	def send_one(self, req, resp, item):
		resp.content_type, resp.body = self.serialize_one(req, item)
		
		
	def send_list(self, req, resp, items):
		resp.content_type, resp.body = self.serialize_list(req, items)
		
		
	def serialize_one(self, req, data):
		return self.serialize(req, 'get_individual_response', data)
		
			
	def serialize_list(self, req, data):
		return self.serialize(req, 'get_collection_response', data)
			
			
	def serialize(self, req, method_name, data):
		view = self.get_view(req)
		method = getattr(view, method_name)
		try:
			return method(req, data)
		except Exception, e:
			self.logger.exception('Failed to serialize response.')
			raise falcon.HTTPInternalServerError()
			
			
	def get_view(self, req):
		"""Get the correct view based on the Accept header"""
		_, view = View.choose(req, self.views)
		return view
			
			
	def get_fields_from_request(self, req):
		"""Unserializes the request body based on the request's content type"""
		for serializer in self.accept_serializers:
			if serializer.mimetype == req.content_type:
				try:
					return serializer.unserialize(req.stream)
				except Exception:
					self.logger.exception('Could not parse request body.')
					raise falcon.HTTPBadRequest('Bad Request', 'Could not parse request body.')
		raise falcon.HTTPUnsupportedMediaType(
			'The supported types are: %s' % ', '.join([x.mimetype for x in self.accept_serializers]))
		
		
	def get_list_params(self, req):
		"""Parse out the filter, sort, offset and limit parameters from a request"""
		return (
			self.get_param(req, 'filter', json.loads),
			self.get_param(req, 'sort', json.loads),
			self.get_param(req, 'offset', int, default=0),
			self.get_param(req, 'limit', int, default=0),
			self.get_show_hidden(req)
		)
		
		
	def get_show_hidden(self, req):
		return self.get_param(req, 'show_hidden', lambda x: True if x.lower() == 'true' or x == '1' else False, default=False)
		
		
	def get_param(self, req, param_name, parsing_fn, required=False, default=None):
		"""Get a parsed query param"""
		param = req.get_param(param_name)
		if not param:
			if required:
				raise falcon.HTTPBadRequest("Bad Request", "Missing required %s parameter" % param_name)
			return default
		try:
			return parsing_fn(param)
		except:
			raise falcon.HTTPBadRequest("Bad Request", "Could not parse %s parameter" % param_name)
		
			
			
			
class Endpoint(object):
	
	def __init__(self, resource, methods):
		self.resource = resource
		self.register_methods(methods)
		
		
	def register_methods(self, methods):
		for method in methods:
			fn = getattr(self, method)
			for http_method in get_http_methods(method):
				setattr(self, 'on_%s' % http_method, fn)
			

class ListEndpoint(Endpoint):
	
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
		return self.resource.get_link_or_reference(req, resp, id, self.reference_name)
		
		
		
def not_found_handler(exc, req, resp, params):
	raise falcon.HTTPNotFound()


def not_authenticated_handler(exc, req, resp, params):
	raise falcon.HTTPUnauthorized('Unauthorized', 'You must authenticate to access this resource.')
	
	
def not_authorized_handler(exc, req, resp, params):
	raise falcon.HTTPForbidden('Forbidden', 'You are not allowed to access this resource.')
	
	
def validation_error_handler(views, exc, req, resp, params):
	_, view = View.choose(req, views)
	resp.content_type, resp.body = view.get_individual_response(req, exc.errors)
	resp.status = falcon.HTTP_400
	
	
def disabled_field_error(exc, req, resp, params):
	raise falcon.HTTPUnauthorized('Unauthorized', exc.message)
		
		
def add_to_falcon(falcon_api, hammock_api, views):
	views_by_type = []
	
	for v in views:
		for mimetype, _ in v.serializers:
			views_by_type.append((mimetype, v))
			
	falcon_api.add_error_handler(errors.NotFoundError, not_found_handler)
	falcon_api.add_error_handler(errors.NotAuthenticatedError, not_authenticated_handler)
	falcon_api.add_error_handler(errors.NotAuthorizedError, not_authorized_handler)
	validation_error_handler_with_views = functools.partial(validation_error_handler, views_by_type)
	falcon_api.add_error_handler(errors.CompoundValidationError, validation_error_handler_with_views)
	falcon_api.add_error_handler(errors.DisabledFieldError, disabled_field_error)
	
	for collection in hammock_api.collections_by_class_name.values():
		resource = Resource(collection, views_by_type)
		resource.add_to_falcon(falcon_api)
		