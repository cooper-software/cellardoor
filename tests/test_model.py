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
        
        
    def test_default_hooks(self):
        """
        on_* methods the entity defines are automatically registered as hooks
        """
        class Foo(Entity):
            
            def __init__(self, *args, **kwargs):
                super(Foo, self).__init__(*args, **kwargs)
                self.called_hook = None
            
            def on_pre_create(self, *args, **kwargs):
                self.called_hook = 'pre_create'
                
            def on_post_create(self, *args, **kwargs):
                self.called_hook = 'post_create'
                
            def on_pre_update(self, *args, **kwargs):
                self.called_hook = 'pre_update'
                
            def on_post_update(self, *args, **kwargs):
                self.called_hook = 'post_update'
                
            def on_pre_delete(self, *args, **kwargs):
                self.called_hook = 'pre_delete'
                
            def on_post_delete(self, *args, **kwargs):
                self.called_hook = 'post_delete'
        
        foo1 = Foo()
        foo1.hooks.trigger_pre('create')
        self.assertEquals(foo1.called_hook, 'pre_create')
        
        foo2 = Foo()
        foo2.hooks.trigger_post('create')
        self.assertEquals(foo2.called_hook, 'post_create')
        
        foo3 = Foo()
        foo3.hooks.trigger_pre('update')
        self.assertEquals(foo3.called_hook, 'pre_update')
        
        foo4 = Foo()
        foo4.hooks.trigger_post('update')
        self.assertEquals(foo4.called_hook, 'post_update')
        
        foo5 = Foo()
        foo5.hooks.trigger_pre('delete')
        self.assertEquals(foo5.called_hook, 'pre_delete')
        
        foo6 = Foo()
        foo6.hooks.trigger_post('delete')
        self.assertEquals(foo6.called_hook, 'post_delete')
        
        
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
        
        
    def test_inherited_mixins(self):
        """Mixin fields should be inherited"""
        
        class Fooable(object):
            foo = Text()
            
            
        class Barable(object):
            bar = Text()
            
            
        class Thing(Entity):
            mixins = (Fooable,)
            
            
        class SpecificThing(Thing):
            mixins = (Barable,)
            
        st = SpecificThing()
        self.assertTrue(hasattr(st, 'foo'))
        self.assertTrue(hasattr(st, 'bar'))
        
        
    def test_inherited_mixins(self):
        """Mixin hooks should be inherited"""
        
        class Fooable(object):
            def on_pre_create(self, fields):
                fields['foo'] = 1
            
        class Barable(object):
            def on_pre_create(self, fields):
                fields['bar'] = 1
            
            
        class Thing(Entity):
            mixins = (Fooable,)
            
            
        class SpecificThing(Thing):
            mixins = (Barable,)
            
        st = SpecificThing()
        fields = {}
        st.hooks.trigger_pre('create', fields)
        self.assertEquals(fields, {'foo':1, 'bar':1})
        
        
        
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
