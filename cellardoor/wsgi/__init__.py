from urlparse import parse_qs
from cellardoor.serializers import JSONSerializer
from cellardoor.errors import ParseError

params_serializer = JSONSerializer()

def parse_params(environ, *include):
	"""Parse out the filter, sort, etc., parameters from a request"""
	if environ.get('QUERY_STRING'):
		params = parse_qs(environ['QUERY_STRING'])
	else:
		params = {}
	param_handlers = (
		('embedded', params_serializer.unserialize_string, None),
		('filter', params_serializer.unserialize_string, None),
		('sort', params_serializer.unserialize_string, None),
		('offset', int, 0),
		('limit', int, 0),
		('show_hidden', bool_field, False)
	)
	results = {}
	if len(include) > 0:
		include = set(include)
	else:
		include = None
		
	for name, fn, default in param_handlers:
		if include and name not in include:
			continue
		results[name] = parse_param(params, name, fn, default=default)
		
	if not include or 'context' in include:
		results['context'] = get_context(environ)
	return results
	
	
def bool_field(value):
	return True if value.lower() == 'true' or value == '1' else False
	
	
def parse_param(params, param_name, parsing_fn, default=None):
	"""Get a parsed query param"""
	param = params.get(param_name, [None])[0]
	if not param:
		return default
	try:
		return parsing_fn(param)
	except Exception, e:
		raise ParseError("Could not parse %s parameter: %s" % (param_name, param))
		
		
def get_context(environ):
	context = {}
	identity = environ.get('cellardoor.identity')
	if identity:
		context['identity'] = identity
	return context
	