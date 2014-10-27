import functools
import falcon
import json
import logging
import inspect
from ..methods import LIST, CREATE, GET, REPLACE, UPDATE, DELETE, get_http_methods
from ..serializers import JSONSerializer, MsgPackSerializer
from ..views import View
from ..views.minimal import MinimalView
from .. import errors

__all__ = ['add_to_falcon']


class Resource(object):
	"""
	A resource exposes an interface through falcon
	"""
	
	# The types of content that are accepted.
	accept_serializers = (JSONSerializer(), MsgPackSerializer())
	
	
	def __init__(self, interface, views):
		self.interface = interface
		self.views = views
		self.logger = logging.getLogger(__name__)
		
		
	def add_to_falcon(self, app):
		methods = self.interface.rules.enabled_methods
		interface_methods = methods.intersection((LIST, CREATE))
		individual_methods = methods.intersection((GET, REPLACE, UPDATE, DELETE))
		
		if not interface_methods and not individual_methods:
			raise Exception, "The '%s' interface exposes no methods" % self.interface.plural_name
		
		if interface_methods:
			app.add_route('/%s' % self.interface.plural_name, ListEndpoint(self, interface_methods))
			
		if individual_methods:
			app.add_route('/%s/{id}' % self.interface.plural_name, IndividualEndpoint(self, individual_methods))
		
		for link_name, link in self.interface.entity.links:
			if self.interface.api.get_interface_for_entity(link.entity):
				app.add_route('/%s/{id}/%s' % (self.interface.plural_name, link_name), 
					ReferenceEndpoint(self, link_name))
			
	
	def list(self, req, resp):
		kwargs = self.get_kwargs(req)
		items = self.interface.list(**kwargs)
		self.send_list(req, resp, items)
		
		
	def count(self, req, resp):
		kwargs = self.get_kwargs(req)
		kwargs['count'] = True
		result = self.interface.list(**kwargs)
		resp.content_type, _ = View.choose(req, self.views)
		resp.set_header('X-Count', str(result))
		
		
	def create(self, req, resp):
		fields = self.get_fields_from_request(req)
		kwargs = self.get_kwargs(req, 'show_hidden', 'context', 'embedded')
		item = self.interface.create(fields, **kwargs)
		resp.status = falcon.HTTP_201
		self.send_one(req, resp, item)
		
	
	def get(self, req, resp, id):
		kwargs = self.get_kwargs(req, 'show_hidden', 'context', 'embedded')
		item = self.interface.get(id, **kwargs)
		self.send_one(req, resp, item)
		
		
	def update(self, req, resp, id):
		fields = self.get_fields_from_request(req)
		kwargs = self.get_kwargs(req, 'show_hidden', 'context', 'embedded')
		item = self.interface.update(id, fields, **kwargs)
		self.send_one(req, resp, item)
		
		
	def replace(self, req, resp, id):
		fields = self.get_fields_from_request(req)
		kwargs = self.get_kwargs(req, 'show_hidden', 'context', 'embedded')
		item = self.interface.replace(id, fields, **kwargs)
		self.send_one(req, resp, item)
		
		
	def delete(self, req, resp, id):
		self.interface.delete(id, context=self.get_context(req))
		
		
	def get_link_or_reference(self, req, resp, id, link_name):
		kwargs = self.get_kwargs(req)
		result = self.interface.link(id, link_name, **kwargs)
		if isinstance(result, dict):
			self.send_one(req, resp, result)
		else:
			self.send_list(req, resp, result)
			
			
	def count_link_or_reference(self, req, resp, id, link_name):
		kwargs = self.get_kwargs(req)
		kwargs['count'] = True
		result = self.interface.link(id, link_name, **kwargs)
		resp.content_type, _ = View.choose(req, self.views)
		if isinstance(result, int):
			resp.set_header('X-Count', str(result))
		
		
	def send_one(self, req, resp, item):
		resp.content_type, resp.body = self.serialize_one(req, item)
		
		
	def send_list(self, req, resp, items):
		resp.content_type, resp.body = self.serialize_list(req, items)
		
		
	def serialize_one(self, req, data):
		return self.serialize(req, 'get_individual_response', data)
		
			
	def serialize_list(self, req, data):
		return self.serialize(req, 'get_list_response', data)
			
			
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
			if req.content_type.startswith( serializer.mimetype ):
				try:
					return serializer.unserialize(req.stream)
				except Exception:
					self.logger.exception('Could not parse request body.')
					raise falcon.HTTPBadRequest('Bad Request', 'Could not parse request body.')
		raise falcon.HTTPUnsupportedMediaType(
			'The supported types are: %s' % ', '.join([x.mimetype for x in self.accept_serializers]))
		
		
	def get_kwargs(self, req, *include):
		"""Parse out the filter, sort, etc., parameters from a request"""
		params = (
			('embedded', json.loads, None),
			('filter', json.loads, None),
			('sort', json.loads, None),
			('offset', int, 0),
			('limit', int, 0),
			('show_hidden', self.bool_field, False)
		)
		results = {}
		if len(include) > 0:
			include = set(include)
		else:
			include = None
		for name, fn, default in params:
			if include and name not in include:
				continue
			results[name] = self.get_param(req, name, fn, default=default)
			
		if not include or 'context' in include:
			results['context'] = self.get_context(req)
		return results
		
		
	def bool_field(self, value):
		return True if value.lower() == 'true' or value == '1' else False
		
		
	def get_param(self, req, param_name, parsing_fn, required=False, default=None):
		"""Get a parsed query param"""
		param = req.get_param(param_name)
		if not param:
			if required:
				raise falcon.HTTPBadRequest("Bad Request", "Missing required %s parameter" % param_name)
			return default
		try:
			return parsing_fn(param)
		except Exception, e:
			raise falcon.HTTPBadRequest("Bad Request", "Could not parse %s parameter" % param_name)
			
			
	def get_context(self, req):
		context = {}
		identity = req.env.get('cellardoor.identity')
		if identity:
			context['identity'] = identity
		return context
		
			
			
			
class Endpoint(object):
	
	def __init__(self, resource, methods):
		self.resource = resource
		self.register_methods(methods)
		
		
	def register_methods(self, methods):
		for method in methods:
			fn = getattr(self, method)
			for http_method in get_http_methods(method):
				setattr(self, 'on_%s' % http_method, fn)
		if LIST in methods:
			setattr(self, 'on_head', self.count)
			

class ListEndpoint(Endpoint):
	
	def list(self, req, resp):
		return self.resource.list(req, resp)
		
		
	def count(self, req, resp):
		return self.resource.count(req, resp)
		
		
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
	
	def __init__(self, resource, link_name):
		self.resource = resource
		self.link_name = link_name
		
		
	def on_get(self, req, resp, id):
		return self.resource.get_link_or_reference(req, resp, id, self.link_name)
		
		
	def on_head(self, req, resp, id):
		return self.resource.count_link_or_reference(req, resp, id, self.link_name)
		
		
		
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
	
	
def duplicate_field_error(views, exc, req, resp, params):
	error = {}
	error[exc.message] = 'A duplicate value already exists.'
	_, view = View.choose(req, views)
	resp.content_type, resp.body = view.get_individual_response(req, error)
	resp.status = falcon.HTTP_400
		
		
class FalconApp(object):
	
	def __init__(self, api, falcon_app=None, views=(MinimalView,)):
		if falcon_app is None:
			falcon_app = falcon.API()
		self.falcon_app = falcon_app
		self.api = api
		
		views_by_type = []
		
		for v in views:
			if inspect.isclass(v):
				v = v()
			for mimetype, _ in v.serializers:
				views_by_type.append((mimetype, v))
				
		falcon_app.add_error_handler(errors.NotFoundError, not_found_handler)
		falcon_app.add_error_handler(errors.NotAuthenticatedError, not_authenticated_handler)
		falcon_app.add_error_handler(errors.NotAuthorizedError, not_authorized_handler)
		validation_error_handler_with_views = functools.partial(validation_error_handler, views_by_type)
		falcon_app.add_error_handler(errors.CompoundValidationError, validation_error_handler_with_views)
		falcon_app.add_error_handler(errors.DisabledFieldError, disabled_field_error)
		duplicate_field_error_with_views = functools.partial(duplicate_field_error, views_by_type)
		falcon_app.add_error_handler(errors.DuplicateError, duplicate_field_error_with_views)
		
		for interface in api.interfaces.values():
			resource = Resource(interface, views_by_type)
			resource.add_to_falcon(falcon_app)
			
			
	def __call__(self, *args, **kwargs):
		return self.falcon_app(*args, **kwargs)