import inspect
from functools import wraps
import logging
import collections
from flask import Blueprint, request, abort, make_response
from flask.views import MethodView
from cellardoor import errors
from cellardoor.serializers import JSONSerializer, MsgPackSerializer
from cellardoor.wsgi import parse_params, get_context
from cellardoor.views.minimal import MinimalView
from cellardoor.views import View
from cellardoor.api.methods import LIST, CREATE, GET, UPDATE, REPLACE, DELETE

class Resource(MethodView):
	
	def response(self, content, status_code=200):
		_, view = View.choose(request.headers.get('accept'), self.views)
		serialize_fn = view.get_list_response if isinstance(content, collections.Sequence) else view.get_individual_response
		content_type, body = serialize_fn(request.headers.get('accept'), content)
		res = make_response(body)
		res.status_code = status_code
		res.headers['content-type'] = content_type
		return res
		
		
	def parse_params(self, *args):
		return parse_params(request.environ, *args)
		
		
	def get_fields_from_request(self):
		for serializer in self.accept_serializers:
			if request.headers.get('content-type', '').startswith( serializer.mimetype ):
				try:
					return serializer.unserialize(request.stream)
				except Exception:
					self.logger.exception('Could not parse request body.')
					abort(400)
		abort(415)


class EntityResource(Resource):
	
	accept_serializers = (JSONSerializer(), MsgPackSerializer())
	
	def __init__(self, interface, views):
		self.interface = interface
		self.views = views
		self.logger = logging.getLogger(__name__)
		
		
	def get(self, id):
		if id:
			kwargs = self.parse_params('show_hidden', 'context', 'embedded')
			item = self.interface.get(id, **kwargs)
			return self.response(item)
		else:
			kwargs = self.parse_params()
			items = self.interface.list(**kwargs)
			return self.response(items)
		
		
	def head(self):
		kwargs = self.parse_params()
		kwargs['count'] = True
		count = self.interface.list(**kwargs)
		res = make_response('')
		res.headers['Content-Type'], _ = View.choose(request.headers.get('accept'), self.views)
		res.headers['X-Count'] = str(count)
		return res
		
		
	def post(self):
		fields = self.get_fields_from_request()
		kwargs = self.parse_params('show_hidden', 'context', 'embedded')
		try:
			item = self.interface.create(fields, **kwargs)
		except errors.CompoundValidationError, e:
			return self.response(e.errors, status_code=400)
		return self.response(item, status_code=201)
		
		
	def put(self, id):
		fields = self.get_fields_from_request()
		kwargs = self.parse_params('show_hidden', 'context', 'embedded')
		item = self.interface.replace(id, fields, **kwargs)
		return self.response(item)
		
		
	def patch(self, id):
		fields = self.get_fields_from_request()
		kwargs = self.parse_params('show_hidden', 'context', 'embedded')
		item = self.interface.update(id, fields, **kwargs)
		return self.response(item)
		
		
	def delete(self, id):
		self.interface.delete(id, context=get_context(request.environ))
		return ''
	
	
class LinkResource(Resource):
	
	def __init__(self, interface, link_name, views):
		self.interface = interface
		self.link_name = link_name
		self.views = views
		
		
	def get(self, id):
		kwargs = self.parse_params()
		result = self.interface.link(id, self.link_name, **kwargs)
		return self.response(result)
		
		
	def head(self, id):
		kwargs = self.parse_params()
		kwargs['count'] = True
		count = self.interface.link(id, self.link_name, **kwargs)
		res = make_response('')
		res.headers['content-type'], _ = View.choose(request.headers.get('accept'), self.views)
		res.headers['X-Count'] = str(count)
		return res


def error_response(code, item=None, views=[]):
	if not item:
		abort(code)
	else:
		_, view = View.choose(request.headers.get('accept'), views)
		content_type, body = view.get_individual_response(request.headers.get('accept'), item)
		res = make_response(body)
		res.status_code = code
		res.headers['content-type'] = content_type
		return res

def handle_errors(fn, views):
	@wraps(fn)
	def wrapper(*args, **kwargs):
		try:
			return fn(*args, **kwargs)
		except errors.NotFoundError:
			return error_response(404, views=views)
		except errors.NotAuthenticatedError:
			return error_response(401, views=views)
		except errors.NotAuthorizedError:
			return error_response(403, views=views)
		except errors.CompoundValidationError, e:
			return error_response(400, e.errors, views=views)
		except errors.DisabledFieldError:
			return error_response(401, views=views)
		except errors.DuplicateError, e:
			return error_response(400, {e.message:'A duplicate already exists.'}, views=views)
		except errors.ParseError, e:
			return error_response(400, e.message, views=views)
	return wrapper
		
		
def create_blueprint(api, name="api", import_name=__name__, views=(MinimalView,)):
	bp = Blueprint(name, import_name)
	
	views_by_type = []
	
	for v in views:
		if inspect.isclass(v):
			v = v()
		for mimetype, _ in v.serializers:
			views_by_type.append((mimetype, v))
	
	for interface_name, interface in api.interfaces.items():
		view = handle_errors(EntityResource.as_view(interface_name, interface, views_by_type), views_by_type)
		if LIST in interface.rules.enabled_methods:
			bp.add_url_rule(
				'/%s/' % interface_name,
				defaults={'id':None},
				view_func=view,
				methods=['GET']
			)
			bp.add_url_rule(
				'/%s/' % interface_name,
				view_func=view,
				methods=['HEAD']
			)
		if CREATE in interface.rules.enabled_methods:
			bp.add_url_rule(
				'/%s/' % interface_name,
				view_func=view,
				methods=['POST']
			)
		if GET in interface.rules.enabled_methods:
			bp.add_url_rule(
				'/%s/<id>' % interface_name,
				view_func=view,
				methods=['GET']
			)
		if UPDATE in interface.rules.enabled_methods:
			bp.add_url_rule(
				'/%s/<id>' % interface_name,
				view_func=view,
				methods=['PATCH']
			)
		if REPLACE in interface.rules.enabled_methods:
			bp.add_url_rule(
				'/%s/<id>' % interface_name,
				view_func=view,
				methods=['PUT']
			)
		if DELETE in interface.rules.enabled_methods:
			bp.add_url_rule(
				'/%s/<id>' % interface_name,
				view_func=view,
				methods=['DELETE']
			)
		for link_name, link in interface.entity.get_links().items():
			if interface.api.get_interface_for_entity(link.entity):
				link_view = handle_errors(LinkResource.as_view('%s.%s' % (interface_name, link_name), interface, link_name, views_by_type), views_by_type)
				trailing_slash = '/' if interface.entity.is_multiple_link(getattr(interface.entity, link_name)) else ''
				bp.add_url_rule(
					'/%s/<id>/%s%s' % (interface_name, link_name, trailing_slash),
					view_func=link_view,
					methods=['GET', 'HEAD']
				)
	return bp
	