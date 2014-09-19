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
		
		
	def __eq__(self, other):
		raise NotImplementedError
		
		
	def require_auth_expr(self, other):
		if not isinstance(other, AuthenticationExpression):
			raise TypeError, "Type '%s' is incompatible with type '%s'" % (type(self).__name__, type(other).__name__)
			
			
	def uses(self, key):
		raise NotImplementedError
			
			
			
class BinaryExpression(AuthenticationExpression):
	
	def __init__(self, a, b):
		self.a = a
		self.b = b
	
	def uses(self, key):
		return self.a.uses(key) or self.b.uses(key)
		
		
	def __eq__(self, other):
		return isinstance(other, self.__class__) and other.a == self.a and other.b == self.b
		
		
			
class AndExpression(BinaryExpression):
	
	
	def __call__(self, context):
		return self.a(context) and self.b(context)
		
		
	def __repr__(self):
		return 'AndExpression(%s, %s)' % (repr(self.a), repr(self.b))
		
		
		
class OrExpression(BinaryExpression):
		
	def __call__(self, context):
		return self.a(context) or self.b(context)
		


class ObjectProxy(AuthenticationExpression):
	
	def __init__(self, name):
		self.name = name
		
		
	def __eq__(self, other):
		return isinstance(other, ObjectProxy) and other.name == self.name
		
		
	def __getattr__(self, key):
		return ObjectProxyValue(self, key)
		
		
	def __getitem__(self, key):
		return self.__getattr__(key)
		
		
	def __call__(self, context):
		return self.name in context
		
		
	def __repr__(self):
		return 'ObjectProxy(%s)' % self.name
		
		
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
		
		
	def __repr__(self):
		return 'ObjectProxyMatch(%s, %s)' % (repr(self.proxy), repr(self.fn))
		
		
	def __eq__(self, other):
		return isinstance(other, ObjectProxyMatch) and other.proxy == self.proxy and other.fn == self.fn
		
		
	def __call__(self, context):
		obj = context.get(self.proxy.name)
		return self.fn(obj)
		
		
	def uses(self, key):
		return self.proxy.uses(key)
		
		
		
class ObjectProxyValue(AuthenticationExpression):
	
	def __init__(self, proxy, key):
		self.proxy = proxy
		self.key = key
		
		
	def __repr__(self):
		return 'ObjectProxyValue(%s, %s)' % (repr(self.proxy), self.key)
		
		
	def __eq__(self, other):
		return isinstance(other, ObjectProxyValue) and other.proxy == self.proxy and other.key == self.key
		
		
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
	
	opstr = ''
	
	def __init__(self, proxy, other):
		self.proxy = proxy
		self.other = other
		
		
	def __repr__(self):
		return '%s %s %s' % (repr(self.proxy), self.opstr, repr(self.other))
		
	
	def __eq__(self, other):
		return isinstance(other, self.__class__) and other.proxy == self.proxy and other.other == self.other
		
		
	def __call__(self, context):
		a = self.proxy.get_value(context)
		
		if isinstance(self.other, ObjectProxyValue):
			b = self.other.get_value(context)
		else:
			b = self.other
			
		return self.compare(a, b)
			
		
	def compare(self, a, b):
		self
		
		
	def uses(self, key):
		if isinstance(self.other, AuthenticationExpression):
			return self.proxy.uses(key) or self.other.uses(key)
		else:
			return self.proxy.uses(key)
		
		
		
class EqualsComparison(ObjectProxyValueComparison):
	opstr = '=='
	
	def compare(self, a, b):
		return a == b
		
		
class NotEqualsComparison(ObjectProxyValueComparison):
	opstr = '!='
	
	def compare(self, a, b):
		return a != b
		
		
class LessThanComparison(ObjectProxyValueComparison):
	opstr = '<'
	
	def compare(self, a, b):
		return a < b
		
		
class GreaterThanComparison(ObjectProxyValueComparison):
	opstr = '>'
	
	def compare(self, a, b):
		return a > b
		
		
class LessThanEqualComparison(ObjectProxyValueComparison):
	opstr = '<='
	
	def compare(self, a, b):
		return a <= b
		
		
class GreaterThanEqualComparison(ObjectProxyValueComparison):
	opstr = '>='
	
	def compare(self, a, b):
		return a >= b
		
		
class ContainsComparison(ObjectProxyValueComparison):
	opstr = ' in '
	
	def compare(self, a, b):
		return a in b
		
		
identity = ObjectProxy('identity')
item = ObjectProxy('item')
