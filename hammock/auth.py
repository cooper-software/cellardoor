import functools


class AuthenticationExpression(object):
	
	def __call__(self, context):
		raise NotImplementedError
		
		
	def __and__(self, other):
		self.require_auth_expr(other)
		return AndExpression(self, other)
		
		
	def __or__(self, other):
		self.require_auth_expr(other)
		return OrExpression(self, other)
		
		
	def __invert__(self):
		return lambda x: not self(x)
		
		
	def require_auth_expr(self, other):
		if not isinstance(other, AuthenticationExpression):
			raise TypeError, "Type '%s' is incompatible with type '%s'" % (type(self).__name__, type(other).__name__)
			
			
			
class AndExpression(AuthenticationExpression):
	
	def __init__(self, a, b):
		self.a = a
		self.b = b
		
		
	def __call__(self, context):
		return self.a(context) and self.b(context)
		
		
		
class OrExpression(AuthenticationExpression):
	
	def __init__(self, a, b):
		self.a = a
		self.b = b
		
		
	def __call__(self, context):
		return self.a(context) or self.b(context)
		


class ObjectProxy(object):
	
	def __init__(self, name):
		self.name = name
		
		
	def __getattr__(self, key):
		return ObjectProxyValue(self, key)
		
		
	def __getitem__(self, key):
		return self.__getattr__(key)
		
		
	def match(self, fn):
		return ObjectProxyMatch(self, fn)
		
		
		
class ObjectProxyMatch(AuthenticationExpression):
	
	def __init__(self, proxy, fn):
		self.proxy = proxy
		self.fn = fn
		
		
	def __call__(self, context):
		obj = context.get(self.proxy.name)
		return self.fn(obj)
		
		
		
class ObjectProxyValue(object):
	
	def __init__(self, proxy, key):
		self.proxy = proxy
		self.key = key
		
		
	def get_value(self, context):
		obj = context.get(self.proxy.name, {})
		val = obj.get(self.key)
		return val
		
		
	def __eq__(self, other):
		return EqualsComparison(self, other)
		
		
	def __ne__(self, other):
		return NotEqualsComparison(self, other)
		
		
	def __lt__(self, other):
		return LessThanComparison(self, other)
		
		
	def __gt__(self, other):
		return GreaterThanComparison(self, other)
		
		
	def __le__(self, other):
		return LessThanEqualComparison(self, other)
		
		
	def __ge__(self, other):
		return GreaterThanEqualComparison(self, other)
		
		
class ObjectProxyValueComparison(AuthenticationExpression):
	
	def __init__(self, proxy, other):
		self.proxy = proxy
		self.other = other
		
		
	def __call__(self, context):
		a = self.proxy.get_value(context)
		
		if isinstance(self.other, ObjectProxyValue):
			b = self.other.get_value(context)
		else:
			b = self.other
			
		return self.compare(a, b)
			
		
	def compare(self, a, b):
		raise NotImplementedError
		
		
		
class EqualsComparison(ObjectProxyValueComparison):
	
	def compare(self, a, b):
		return a == b
		
		
class NotEqualsComparison(ObjectProxyValueComparison):
	
	def compare(self, a, b):
		return a != b
		
		
class LessThanComparison(ObjectProxyValueComparison):
	
	def compare(self, a, b):
		return a < b
		
		
class GreaterThanComparison(ObjectProxyValueComparison):
	
	def compare(self, a, b):
		return a > b
		
		
class LessThanEqualComparison(ObjectProxyValueComparison):
	
	def compare(self, a, b):
		return a <= b
		
		
class GreaterThanEqualComparison(ObjectProxyValueComparison):
	
	def compare(self, a, b):
		return a >= b
		
		
identity = ObjectProxy('identity')
item = ObjectProxy('item')
