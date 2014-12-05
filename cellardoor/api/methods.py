__all__ = (
	'LIST',
	'GET',
	'CREATE',
	'UPDATE',
	'REPLACE',
	'DELETE',
	'ALL',
	'get_http_methods'
)


LIST = 'list'
GET = 'get'
CREATE = 'create'
REPLACE = 'replace'
UPDATE = 'update'
DELETE = 'delete'

ALL = (LIST, GET, CREATE, UPDATE, REPLACE, DELETE)

_http_methods = {
	LIST: ('get',),
	GET: ('get',),
	CREATE: ('post',),
	REPLACE: ('put',),
	UPDATE: ('patch',),
	DELETE: ('delete',)
}

def get_http_methods(method):
	return _http_methods[method]
	