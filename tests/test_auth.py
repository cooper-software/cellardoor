import unittest
from hammock.auth import *

class TestAuth(unittest.TestCase):
	
	def test_auth_expr_abstract(self):
		"""A base auth expression can't be called"""
		expr = AuthenticationExpression()
		
		with self.assertRaises(NotImplementedError):
			expr({})
			
			
	def test_auth_expr_and_fail(self):
		"""An auth expression and'd with an expression of another type raises an exception"""
		expr = AuthenticationExpression()
		
		with self.assertRaises(TypeError):
			expr & 23
			
			
	def test_auth_expr_or_fail(self):
		"""An auth expression or'd with an expression of another type raises an exception"""
		expr = AuthenticationExpression()
		
		with self.assertRaises(TypeError):
			expr | 23
			
			
	def test_auth_expr_and(self):
		"""And'ing two auth expressions creates another auth expression that is the logical AND of the two expressions"""
		
		class IdentityExpr(AuthenticationExpression):
			
			def __init__(self, val):
				self.val = val
			
			def __call__(self, context):
				return self.val
				
				
				
		true_expr = IdentityExpr(True)
		false_expr = IdentityExpr(False)
		
		and_expr = true_expr & false_expr
		self.assertIsInstance(and_expr, AuthenticationExpression)
		
		self.assertTrue((true_expr & true_expr)({}))
		self.assertFalse((true_expr & false_expr)({}))
		self.assertFalse((false_expr & false_expr)({}))
		
		
	def test_auth_expr_or(self):
		"""And'ing two auth expressions creates another auth expression that is the logical OR of the two expressions"""
		
		class IdentityExpr(AuthenticationExpression):
			
			def __init__(self, val):
				self.val = val
			
			def __call__(self, context):
				return self.val
				
				
				
		true_expr = IdentityExpr(True)
		false_expr = IdentityExpr(False)
		
		and_expr = true_expr | false_expr
		self.assertIsInstance(and_expr, AuthenticationExpression)
		
		self.assertTrue((true_expr | true_expr)({}))
		self.assertTrue((true_expr | false_expr)({}))
		self.assertFalse((false_expr | false_expr)({}))
		
		
	def test_auth_expr_invert(self):
		"""Inverting an auth expression negates it"""
		
		class TrueExpr(AuthenticationExpression):
			
			def __call__(self, context):
				return True
				
		expr = TrueExpr()
		not_expr = ~expr
		self.assertEquals(expr({}), True)
		self.assertEquals(not_expr({}), False)
		
		
	def test_object_proxy_match(self):
		"""A match operation evaluates against an item in the context"""
		proxy = ObjectProxy('foo')
		expr = proxy.match(lambda x: x['bar'] == 23)
		self.assertTrue(expr({'foo':{'bar':23}}))
		
		
	def test_object_proxy_get(self):
		"""Getting an item or attribute from an ObjectProxy returns and ObjectProxyValue"""
		proxy = ObjectProxy('foo')
		
		item = proxy['bar']
		self.assertIsInstance(item, ObjectProxyValue)
		
		attr = proxy.bar
		self.assertIsInstance(item, ObjectProxyValue)
		
		
	def test_object_proxy_nonexistent(self):
		"""An object project value returns None for a non-existint context item"""
		proxy = ObjectProxy('foo')
		proxy_value = proxy.bar
		result = proxy_value.get_value({})
		self.assertEquals(result, None)
		
		
	def test_object_proxy_value_nonexistent(self):
		"""An object project value returns None for a non-existint context item key"""
		proxy = ObjectProxy('foo')
		proxy_value = proxy.bar
		result = proxy_value.get_value({'foo':{'baz':23}})
		self.assertEquals(result, None)
		
		
	def test_object_proxy_value_nonexists(self):
		"""An object project value returns the value of a context item key"""
		proxy = ObjectProxy('foo')
		proxy_value = proxy.bar
		result = proxy_value.get_value({'foo':{'bar':23}})
		self.assertEquals(result, 23)
		
		
	def test_proxy_equals(self):
		a = ObjectProxy('foo').bar
		b = ObjectProxy('foo').baz
		c = 5
		
		context = {'foo': { 'bar':5, 'baz':5 }}
		self.assertTrue(
			(a == b == c)(context)
		)
		
		context = {'foo': { 'bar':4, 'baz':4 }}
		self.assertFalse(
			(a == b == c)(context)
		)
		
		context = {'foo': { 'bar':3, 'baz':4 }}
		self.assertFalse(
			(a == b == c)(context)
		)
		
	def test_proxy_not_equals(self):
		a = ObjectProxy('foo').bar
		b = ObjectProxy('foo').baz
		c = 5
		
		context = {'foo': { 'bar':4, 'baz':5 }}
		self.assertTrue(
			(a != b)(context)
		)
		
		context = {'foo': { 'bar':5, 'baz':5 }}
		self.assertFalse(
			(a != b)(context)
		)
		
		context = {'foo': { 'bar':4 }}
		self.assertTrue(
			(a != c)(context)
		)
		
		context = {'foo': { 'bar':5 }}
		self.assertFalse(
			(a != c)(context)
		)
		
		
	def test_proxy_less_than(self):
		a = ObjectProxy('foo').bar
		b = ObjectProxy('foo').baz
		c = 5
		
		context = {'foo': { 'bar':4, 'baz':5 }}
		self.assertTrue(
			(a < b)(context)
		)
		
		context = {'foo': { 'bar':5, 'baz':5 }}
		self.assertFalse(
			(a < b)(context)
		)
		
		context = {'foo': { 'bar':4 }}
		self.assertTrue(
			(a < c)(context)
		)
		
		context = {'foo': { 'bar':5 }}
		self.assertFalse(
			(a < c)(context)
		)
		
		
	def test_proxy_greater_than(self):
		a = ObjectProxy('foo').bar
		b = ObjectProxy('foo').baz
		c = 5
		
		context = {'foo': { 'bar':5, 'baz':4 }}
		self.assertTrue(
			(a > b)(context)
		)
		
		context = {'foo': { 'bar':5, 'baz':5 }}
		self.assertFalse(
			(a > b)(context)
		)
		
		context = {'foo': { 'bar':6 }}
		self.assertTrue(
			(a > c)(context)
		)
		
		context = {'foo': { 'bar':4 }}
		self.assertFalse(
			(a > c)(context)
		)
		
		
	def test_proxy_less_than_equal(self):
		a = ObjectProxy('foo').bar
		b = ObjectProxy('foo').baz
		c = 5
		
		context = {'foo': { 'bar':4, 'baz':5 }}
		self.assertTrue(
			(a <= b)(context)
		)
		
		context = {'foo': { 'bar':5, 'baz':5 }}
		self.assertTrue(
			(a <= b)(context)
		)
		
		context = {'foo': { 'bar':6, 'baz':5 }}
		self.assertFalse(
			(a <= b)(context)
		)
		
		context = {'foo': { 'bar':4 }}
		self.assertTrue(
			(a <= c)(context)
		)
		
		context = {'foo': { 'bar':5 }}
		self.assertTrue(
			(a <= c)(context)
		)
		
		context = {'foo': { 'bar':6 }}
		self.assertFalse(
			(a <= c)(context)
		)
		
		
	def test_proxy_greater_than_equal(self):
		a = ObjectProxy('foo').bar
		b = ObjectProxy('foo').baz
		c = 5
		
		context = {'foo': { 'bar':5, 'baz':4 }}
		self.assertTrue(
			(a >= b)(context)
		)
		
		context = {'foo': { 'bar':5, 'baz':5 }}
		self.assertTrue(
			(a >= b)(context)
		)
		
		context = {'foo': { 'bar':5, 'baz':6 }}
		self.assertFalse(
			(a >= b)(context)
		)
		
		context = {'foo': { 'bar':6 }}
		self.assertTrue(
			(a >= c)(context)
		)
		
		context = {'foo': { 'bar':5 }}
		self.assertTrue(
			(a >= c)(context)
		)
		
		context = {'foo': { 'bar':4 }}
		self.assertFalse(
			(a >= c)(context)
		)
		