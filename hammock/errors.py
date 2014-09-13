class NotFoundError(Exception):
	pass
	
	
class AuthenticationError(Exception):
	pass
	
	
from model import ValidationError, CompoundValidationError