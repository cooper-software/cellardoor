import unittest
from mock import Mock
from cellardoor.events import EventManager


class TestEventManager(unittest.TestCase):
	
	def test_event_manager(self):
		before_foo = Mock()
		after_foo = Mock()
		before_bar = Mock()
		
		events = EventManager('foo', 'bar')
		events.before_foo(before_foo)
		events.fire_before_foo(123)
		before_foo.assert_called_once_with(123)
		self.assertFalse(after_foo.called)
		self.assertFalse(before_bar.called)
		
		before_foo = Mock()
		
		events.after_foo(after_foo)
		events.fire_after_foo(321)
		after_foo.assert_called_once_with(321)
		self.assertFalse(before_foo.called)
		self.assertFalse(before_bar.called)
		
		before_foo = Mock()
		after_foo = Mock()
		
		events.before_bar(before_bar)
		events.fire_before_bar('skidoo')
		before_bar.assert_called_once_with('skidoo')
		self.assertFalse(before_foo.called)
		self.assertFalse(after_foo.called)
		
		before_foo = Mock()
		after_foo = Mock()
		before_bar = Mock()
		
		events.after_foo(after_foo)
		events.fire_after_foo(321)
		after_foo.assert_called_once_with(321)
		self.assertFalse(before_foo.called)
		self.assertFalse(before_bar.called)