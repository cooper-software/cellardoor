import unittest
from datetime import datetime
from cellardoor.model.mixins import *


class TestTimestampedMixin(unittest.TestCase):
        
    def test_timestamped_mixin(self):
        t = Timestamped()
        self.assertTrue(hasattr(t, 'on_pre_create'))
        self.assertTrue(hasattr(t, 'on_pre_update'))
        
        fields = {}
        t.on_pre_create(fields)
        self.assertIn('created', fields)
        self.assertIn('modified', fields)
        self.assertEquals(fields['created'], fields['modified'])
        self.assertIsInstance(fields['created'], datetime)
        
        t.on_pre_update('123', fields)
        self.assertNotEquals(fields['created'], fields['modified'])
        self.assertIsInstance(fields['created'], datetime)
        self.assertIsInstance(fields['modified'], datetime)