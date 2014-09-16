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
			
			
	def uses(self, key):
		raise NotImplementedError
			
			
			
class BinaryExpression(AuthenticationExpression):
	
	def uses(self, key):
		return self.a.uses(key) or self.b.uses(key)
		
		
			
class AndExpression(BinaryExpression):
	
	def __init__(self, a, b):
		self.a = a
		self.b = b
		
		
	def __call__(self, context):
		return self.a(context) and self.b(context)
		
		
		
class OrExpression(BinaryExpression):
	
	def __init__(self, a, b):
		self.a = a
		self.b = b
		
		
	def __call__(self, context):
		return self.a(context) or self.b(context)
		


class ObjectProxy(AuthenticationExpression):
	
	def __init__(self, name):
		self.name = name
		
		
	def __getattr__(self, key):
		return ObjectProxyValue(self, key)
		
		
	def __getitem__(self, key):
		return self.__getattr__(key)
		
		
	def __call__(self, context):
		return self.name in context
		
		
	def match(self, fn):
		return ObjectProxyMatch(self, fn)
		
		
	def exists(self):
		return self
		
		
	def uses(self, key):
		return self.name == key
		
		
		
class ObjectProxyMatch(AuthenticationExpression):
	
	def __init__(self, proxy, fn):
		self.proxy = proxy
		self.fn = fn
		
		
	def __call__(self, context):
		obj = context.get(self.proxy.name)
		return self.fn(obj)
		
		
	def uses(self, key):
		return self.proxy.uses(key)
		
		
		
class ObjectProxyValue(AuthenticationExpression):
	
	def __init__(self, proxy, key):
		self.proxy = proxy
		self.key = key
		
		
	def get_value(self, context):
		obj = context.get(self.proxy.name, {})
		val = obj.get(self.key)
		return val
		
		
	def exists(self):
		return self
		
		
	def uses(self, key):
		return self.proxy.uses(key)
		
		
	def __call__(self, context):
		return self.proxy(context) and self.key in context[self.proxy.name]
		
		
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
		
		
	def __contains__(self, other):
		return ContainsComparison(self, other)
		
		
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
		
		
	def uses(self, key):
		if isinstance(self.other, AuthenticationExpression):
			return self.proxy.uses(key) or self.other.uses(key)
		else:
			return self.proxy.uses(key)
		
		
		
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
		
		
class ContainsComparison(ObjectProxyValueComparison):
	
	def compare(self, a, b):
		return a in b
		
		
identity = ObjectProxy('identity')
result = ObjectProxy('result')
