class NotFoundError(Exception):
	pass
	
	
class NotAuthorizedError(Exception):
	pass
	
	
class NotAuthenticatedError(Exception):
	pass
	
	
class VersionConflictError(Exception):
	
	def __init__(self, other):
		self.other = other
		super(VersionConflictError, self).__init__()
	
	
from model import CompoundValidationError