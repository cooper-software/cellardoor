import falcon
from cStringIO import StringIO

def create_fake_request(method='GET', 
	                    script_name='', 
	                    path_info='', 
	                    query_string='',
	                    content_type='',
	                    content_length=0,
	                    headers=None):
	
	environ = {
		'REQUEST_METHOD': method,
		'SERVER_NAME': 'foo',
		'SERVER_PORT': '80',
		'SCRIPT_NAME': script_name,
		'PATH_INFO': path_info,
		'QUERY_STRING': query_string,
		'CONTENT_TYPE': content_type,
		'CONTENT_LENGTH': content_length,
		'SERVER_PROTOCOL': 'HTTP/1.1',
		'wsgi.version': (1,0),
		'wsgi.url_scheme': 'http',
		'wsgi.input': StringIO(),
		'wsgi.errors': StringIO(),
		'wsgi.multithread': False,
		'wsgi.multiprocess': False,
		'wsgi.run_once': True
	}
	
	if headers:
		for k,v in headers.items():
			k = k.upper().replace('-', '_')
			environ['HTTP_%s' % k] = v
	
	return falcon.Request(environ)