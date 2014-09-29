class Storage(object):
	
	# These are the methods you need to implement
	# to create a new storage class.
	
	
	def setup(self, model):
		pass
		
	
	def get(self, entity, filter=None, fields=None, sort=None, offset=0, limit=0, versions=False, count=False):
		raise NotImplementedError
		
		
	def get_by_ids(self, entity, ids, filter=None, fields=None, sort=None, offset=0, limit=0, versions=False, count=False):
		raise NotImplementedError
		
		
	def get_by_id(self, entity, id, fields=None, version=None):
		raise NotImplementedError
		
		
	def create(self, entity, fields, version_creator=None):
		raise NotImplementedError
		
		
	def update(self, entity, id, fields, replace=False, version_creator=None):
		raise NotImplementedError
		
		
	def delete(self, entity, id, version_creator=None):
		raise NotImplementedError
		
		
	def check_filter(self, filter, allowed_fields):
		raise NotImplementedError