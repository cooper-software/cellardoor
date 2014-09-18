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
		
		
class DisabledFieldError(Exception):
	pass
	
	
class DisabledMethodError(Exception):
	pass
	
	
class DuplicateError(Exception):
	pass
	
	
from model import CompoundValidationError