"""
Unit tests for data fields
"""
import unittest
from cellardoor.model import *


class TestReference(unittest.TestCase):
    pass


class TestEntity(unittest.TestCase):
    
    def test_can_validate(self):
        """
        Should validate against a compound validator of its field attributes.
        """
        class Foo(Entity):
            bar = Text(required=True)
            baz = Text(maxlength=10)
        
        with self.assertRaises(CompoundValidationError):
            Foo.validator.validate({'baz':'x'*11})
        
        obj = {'bar':'x', 'baz':'y'}
        result = Foo.validator.validate(obj)
        self.assertEquals(result, obj)
        
        
    def test_can_turn_off_required(self):
        """
        Should be able to turn off enforcement of required fields
        """
        class Foo(Entity):
            bar = Text(required=True)
            baz = Text()
        
        obj = {'baz':'y'}
        result = Foo.validator.validate(obj, enforce_required=False)
        self.assertEquals(result, obj)
        
        
    def test_hooks(self):
        """
        Entities have an event manager with create, update and delete events
        """
        class Foo(Entity):
            pass
                
        f = Foo()
        f.hooks.pre('create', lambda x: x)
        f.hooks.post('create', lambda x: x)
        f.hooks.pre('update', lambda x: x)
        f.hooks.post('update', lambda x: x)
        f.hooks.pre('delete', lambda x: x)
        f.hooks.post('delete', lambda x: x)
        
        
    def test_multiple_inheritance_fail(self):
        """
        Raises an error when extending more than one Entity
        """
        class Foo(Entity):
            pass
            
        class Bar(Entity):
            pass
            
        with self.assertRaises(Exception) as cm:
            class Baz(Foo, Bar):
                pass
                
        self.assertEquals(cm.exception.message, "Cannot extend more than one Entity")
        
        
    def test_get_entity_hierarchy(self):
        """Can get a list including the entity and all its bases in hierarchical order"""
        class Foo(Entity):
            pass
            
        class Bar(Foo):
            pass
            
            
        class Baz(Bar):
            pass
            
        self.assertEquals(Baz.hierarchy, [Foo, Bar, Baz])
        self.assertEquals(Foo.hierarchy, [Foo])
        self.assertEquals(Foo.children, [Bar, Baz])
        self.assertEquals(Bar.children, [Baz])
        
        
    def test_inheritance_field_summing(self):
        """A descendant should have it's ancestor's fields as well as its own."""
        class Foo(Entity):
            a = Text()
            b = Text()
            
        class Bar(Foo):
            c = Text()
            
        self.assertEquals(set(Bar.fields.keys()), set(['a', 'b', 'c']))
        
        result = Bar.validator.validate({'a':'1','b':'2','c':'3'})
        self.assertEquals(result, {'a':'1','b':'2','c':'3'})
        
        
    def test_visible_fields(self):
        """Has sets for visible and hidden fields"""
        class Foo(Entity):
            a = Text()
            b = Text()
            c = Text(hidden=True)
            d = Reference('Bar')
        
        self.assertEquals(Foo.hidden_fields, {'c'})
        self.assertEquals(Foo.visible_fields, {'a', 'b', 'd'})
        
        
    def test_embeddable(self):
        """Has sets for embeddable and default embedded references"""
        class Foo(Entity):
            a = Reference('Bar')
            b = Reference('Bar', embeddable=True)
            c = Reference('Bar', embeddable=True, embed_by_default=False)
        
        self.assertEquals(Foo.embeddable, {'b', 'c'})
        self.assertEquals(Foo.embed_by_default, {'b'})
        
        
    def test_mixins(self):
        """Can have a list of mixins that add additional fields"""
        class Named(object):
            name = Text()
            
        class Foo(Entity):
            mixins = (Named,)
            
        foo = Foo()
        self.assertTrue(hasattr(foo, 'name'))
        self.assertEquals(foo.name.__class__, Text)
        
        
    def test_mixin_hooks(self):
        """Mixins can have hooks that are registered on an entity"""
        class Fooable(object):
            
            def on_pre_create(self, fields, *args, **kwargs):
                fields['foo'] = 123
                
        class Bar(Entity):
            mixins = (Fooable(),)
            
        bar = Bar()
        fields = {}
        bar.hooks.trigger_pre('create', fields)
        self.assertIn('foo', fields)
        self.assertEquals(fields['foo'], 123)
        
        
        
class TestModel(unittest.TestCase):
    
    def test_unresolvable_link(self):
        """
        Should raise an error if a link can't be resolved
        """
        
        class Foo(Entity):
            bar = Reference('Bar')
        
        with self.assertRaises(Exception):
            model = Model(Foo)
            
            
    def test_foreign_link(self):
        """
        Should raise an error if a link points to an entity that isn't in the model
        """
        class Foo(Entity):
            pass
            
        class Bar(Entity):
            foo = Reference(Foo)
            
        with self.assertRaises(Exception):
            model = Model(Bar)
            
            
    def test_pass(self):
        """
        Should do nothing special when initialized with a well-defined model
        """
        
        class Foo(Entity):
            bar = Reference('Bar')
            
            
        class Bar(Entity):
            foos = ListOf(Reference(Foo))
            
            
        model = Model(None, (Foo, Bar))
        self.assertTrue(model.has_entity(Foo))
        self.assertTrue(model.has_entity(Bar))
        
        
        
if __name__ == "__main__":
    unittest.main()
