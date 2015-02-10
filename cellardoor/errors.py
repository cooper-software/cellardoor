class NotFoundError(Exception):
	pass
	
	
class NotAuthorizedError(Exception):
	pass
	
	
class NotAuthenticatedError(Exception):
	pass
	
	
class IdentificationError(Exception):
	pass
	
	
class VersionConflictError(Exception):
	
	def __init__(self, other):
		self.other = other
		super(VersionConflictError, self).__init__()
		
		
class NotVersionedError(Exception):
	pass
		
		
class DisabledFieldError(Exception):
	pass
	
	
class DisabledMethodError(Exception):
	pass
	
	
class DuplicateError(Exception):
	pass
	
	
class ParseError(Exception):
	pass
	
	
from model import ValidationError, CompoundValidationError