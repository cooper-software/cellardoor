from . import create_fake_request
from cellardoor.views import View
from cellardoor.serializers import Serializer
import unittest


class FooSerializer(Serializer):
	
	def serialize(self, obj):
		return 'Foo'
		
		
class BarSerializer(Serializer):
	
	def serialize(self, obj):
		return 'Bar'
		


class TestView(unittest.TestCase):
	
	def test_abstract_methods(self):
		"""
		View has abstract methods that should raise an error if used
		"""
		view = View()
		
		with self.assertRaises(NotImplementedError):
			view.get_list_response(None, None)
			
			
		with self.assertRaises(NotImplementedError):
			view.get_individual_response(None, None)
			
			
	def test_content_type_negotiation(self):
		"""
		View should pick a serializer to match the Accept header when possible
		"""
		view = View()
		view.serializers = (
			('application/x-foo', FooSerializer()),
			('application/x-bar', BarSerializer())
		)
		
		# No accept header means the first serializer in the list
		content_type, result = view.serialize('', {})
		self.assertEquals(content_type, 'application/x-foo')
		self.assertEquals(result, 'Foo')
		
		# A matching accept header means the matching serializer
		content_type, result = view.serialize('application/x-bar', {})
		self.assertEquals(content_type, 'application/x-bar')
		self.assertEquals(result, 'Bar')
		
		# An unmatched accept header means the first serializer in the list
		content_type, result = view.serialize('text/xml', {})
		self.assertEquals(content_type, 'application/x-foo')
		self.assertEquals(result, 'Foo')
		