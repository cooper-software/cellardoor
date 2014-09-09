class Storage(object):
	
	# These are the methods you need to implement
	# to create a new storage class.
	
	
	def setup(self, model):
		pass
		
	
	def get(self, entity, filter=None, fields=None, sort=None, offset=0, limit=0):
		raise NotImplementedError
		
		
	def create(self, entity, fields):
		raise NotImplementedError
		
		
	def update(self, entity, id, fields, replace=False):
		raise NotImplementedError
		
		
	def delete(self, entity, id):
		raise NotImplementedError
		
		
	# End abstract methods
		
		
		
	def set_model(self, model):
		self.model = model
		self.setup(model)
		