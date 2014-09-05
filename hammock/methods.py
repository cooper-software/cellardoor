__all__ = (
	'LIST', 'GET', 'CREATE', 'UPDATE', 
	'DELETE', 'ALL', 'get_http_methods',
	'get_method_name'
)


LIST = 'list'
GET = 'get'
CREATE = 'create'
UPDATE = 'update'
DELETE = 'delete'
ALL = (LIST, GET, CREATE, UPDATE, DELETE)

_http_methods = {
	LIST: ('get',),
	GET: ('get',),
	CREATE: ('post',),
	UPDATE: ('patch', 'put'),
	DELETE: ('delete',)
}

def get_http_methods(method):
	return _http_methods[method]
	