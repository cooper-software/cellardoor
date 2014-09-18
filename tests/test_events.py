import unittest
from mock import Mock
from hammock.events import EventManager


class TestEventManager(unittest.TestCase):
	
	def test_event_manager(self):
		pre_foo = Mock()
		post_foo = Mock()
		pre_bar = Mock()
		
		events = EventManager('foo', 'bar')
		events.pre('foo', pre_foo)
		events.trigger_pre('foo', 123)
		pre_foo.assert_called_once_with(123)
		self.assertFalse(post_foo.called)
		self.assertFalse(pre_bar.called)
		
		pre_foo = Mock()
		
		events.post('foo', post_foo)
		events.trigger_post('foo', 321)
		post_foo.assert_called_once_with(321)
		self.assertFalse(pre_foo.called)
		self.assertFalse(pre_bar.called)
		
		pre_foo = Mock()
		post_foo = Mock()
		
		events.pre('bar', pre_bar)
		events.trigger_pre('bar', 'skidoo')
		pre_bar.assert_called_once_with('skidoo')
		self.assertFalse(pre_foo.called)
		self.assertFalse(post_foo.called)
		
		pre_foo = Mock()
		post_foo = Mock()
		pre_bar = Mock()
		
		events.post('foo', post_foo)
		events.trigger_post('foo', 321)
		post_foo.assert_called_once_with(321)
		self.assertFalse(pre_foo.called)
		self.assertFalse(pre_bar.called)