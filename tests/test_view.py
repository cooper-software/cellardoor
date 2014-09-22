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
			view.get_collection_response(None, None)
			
			
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
		req = create_fake_request()
		content_type, result = view.serialize(req, {})
		self.assertEquals(content_type, 'application/x-foo')
		self.assertEquals(result, 'Foo')
		
		# A matching accept header means the matching serializer
		req = create_fake_request(headers={'accept':'application/x-bar'})
		content_type, result = view.serialize(req, {})
		self.assertEquals(content_type, 'application/x-bar')
		self.assertEquals(result, 'Bar')
		
		# An unmatched accept header means the first serializer in the list
		req = create_fake_request(headers={'accept':'text/xml'})
		content_type, result = view.serialize(req, {})
		self.assertEquals(content_type, 'application/x-foo')
		self.assertEquals(result, 'Foo')
		