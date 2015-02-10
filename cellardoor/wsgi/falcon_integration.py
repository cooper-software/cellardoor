import functools
import falcon
import logging
import inspect
from cellardoor import errors
from cellardoor.api.methods import LIST, CREATE, GET, REPLACE, UPDATE, DELETE, get_http_methods
from cellardoor.serializers import JSONSerializer, MsgPackSerializer
from cellardoor.views import View
from cellardoor.views.minimal import MinimalView
from cellardoor.wsgi import parse_params, get_context

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
		
		for link_name, link in self.interface.entity.get_links().items():
			if self.interface.api.get_interface_for_entity(link.entity):
				app.add_route('/%s/{id}/%s' % (self.interface.plural_name, link_name), 
					ReferenceEndpoint(self, link_name))
			
	
	def list(self, req, resp):
		kwargs = self.parse_params(req)
		items = self.interface.list(**kwargs)
		self.send_list(req, resp, items)
		
		
	def count(self, req, resp):
		kwargs = self.parse_params(req)
		kwargs['count'] = True
		result = self.interface.list(**kwargs)
		resp.content_type, _ = View.choose(req.get_header('accept'), self.views)
		resp.set_header('X-Count', str(result))
		
		
	def create(self, req, resp):
		fields = self.get_fields_from_request(req)
		kwargs = self.parse_params(req, 'show_hidden', 'context', 'embedded')
		item = self.interface.create(fields, **kwargs)
		resp.status = falcon.HTTP_201
		self.send_one(req, resp, item)
		
	
	def get(self, req, resp, id):
		kwargs = self.parse_params(req, 'show_hidden', 'context', 'embedded')
		item = self.interface.get(id, **kwargs)
		self.send_one(req, resp, item)
		
		
	def update(self, req, resp, id):
		fields = self.get_fields_from_request(req)
		kwargs = self.parse_params(req, 'show_hidden', 'context', 'embedded')
		item = self.interface.update(id, fields, **kwargs)
		self.send_one(req, resp, item)
		
		
	def replace(self, req, resp, id):
		fields = self.get_fields_from_request(req)
		kwargs = self.parse_params(req, 'show_hidden', 'context', 'embedded')
		item = self.interface.replace(id, fields, **kwargs)
		self.send_one(req, resp, item)
		
		
	def delete(self, req, resp, id):
		self.interface.delete(id, context=get_context(req.env))
		
		
	def get_link_or_reference(self, req, resp, id, link_name):
		kwargs = self.parse_params(req)
		result = self.interface.link(id, link_name, **kwargs)
		if isinstance(result, dict):
			self.send_one(req, resp, result)
		else:
			self.send_list(req, resp, result)
			
			
	def count_link_or_reference(self, req, resp, id, link_name):
		kwargs = self.parse_params(req)
		kwargs['count'] = True
		result = self.interface.link(id, link_name, **kwargs)
		resp.content_type, _ = View.choose(req.get_header('accept'), self.views)
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
			return method(req.get_header('accept'), data)
		except Exception, e:
			self.logger.exception('Failed to serialize response.')
			raise falcon.HTTPInternalServerError('Internal Server Error', '')
			
			
	def get_view(self, req):
		"""Get the correct view based on the Accept header"""
		_, view = View.choose(req.get_header('accept'), self.views)
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
		
		
	def parse_params(self, req, *args):
		try:
			return parse_params(req.env, *args)
		except errors.ParseError, e:
			raise falcon.HTTPBadRequest('Bad Request', e.message)
			
			
			
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
	_, view = View.choose(req.get_header('accept'), views)
	resp.content_type, resp.body = view.get_individual_response(req.get_header('accept'), exc.errors)
	resp.status = falcon.HTTP_400
	
	
def disabled_field_error(exc, req, resp, params):
	raise falcon.HTTPUnauthorized('Unauthorized', exc.message)
	
	
def duplicate_field_error(views, exc, req, resp, params):
	error = {}
	error[exc.message] = 'A duplicate value already exists.'
	_, view = View.choose(req.get_header('accept'), views)
	resp.content_type, resp.body = view.get_individual_response(req.get_header('accept'), error)
	resp.status = falcon.HTTP_400
		
		
class FalconApp(object):
	
	def __init__(self, api, falcon_app=None, views=(MinimalView,)):
		if falcon_app is None:
			falcon_app = falcon.API()
		self.falcon_app = falcon_app
		self.api = api
		self.resources = {}
		
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
			self.resources[interface.plural_name] = resource
			
			
	def __call__(self, *args, **kwargs):
		return self.falcon_app(*args, **kwargs)
		