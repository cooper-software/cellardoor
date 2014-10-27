__all__ = [
	'Interface',
	'LIST',
	'GET',
	'CREATE',
	'UPDATE',
	'REPLACE',
	'DELETE',
	'ALL'
]

LIST = 'list'
GET = 'get'
CREATE = 'create'
REPLACE = 'replace'
UPDATE = 'update'
DELETE = 'delete'
ALL = (LIST, GET, CREATE, UPDATE, REPLACE, DELETE)


class InterfaceType(type):
	
	def __new__(cls, name, bases, attrs):
		new_cls = 
		
		
		
class Interface(object):
	
	__metaclass__ = InterfaceType