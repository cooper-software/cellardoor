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
	A resource provides CRUD and query operations for a model
	"""
	
	__metaclass__ = ResourceMeta
	
	model = None
	
	enabled_methods = ()
