"""
Unit tests for data fields
"""
import unittest
from cellardoor.model import *


class TestEntity(unittest.TestCase):
        
    
    def test_can_validate(self):
        """
        Should validate against a compound validator of its field attributes.
        """
        model = Model()
        
        class Foo(model.Entity):
            bar = Text(required=True)
            baz = Text(maxlength=10)
        
        with self.assertRaises(CompoundValidationError):
            model.Foo.validator.validate({'baz':'x'*11})
        
        obj = {'bar':'x', 'baz':'y'}
        result = model.Foo.validator.validate(obj)
        self.assertEquals(result, obj)
        
        
    def test_can_turn_off_required(self):
        """
        Should be able to turn off enforcement of required fields
        """
        model = Model()
        
        class Foo(model.Entity):
            bar = Text(required=True)
            baz = Text()
        
        obj = {'baz':'y'}
        result = model.Foo.validator.validate(obj, enforce_required=False)
        self.assertEquals(result, obj)
        
        
    def test_hooks(self):
        """
        Entities have an event manager with create, update and delete events
        """
        model = Model()
        
        class Foo(model.Entity):
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
        model = Model()
        called_hooks = {}
        
        class Foo(model.Entity):
            
            def on_pre_create(cls, *args, **kwargs):
                called_hooks['pre_create'] = 1
                
            def on_post_create(cls, *args, **kwargs):
                called_hooks['post_create'] = 1
                
            def on_pre_update(cls, *args, **kwargs):
                called_hooks['pre_update'] = 1
                
            def on_post_update(cls, *args, **kwargs):
                called_hooks['post_update'] = 1
                
            def on_pre_delete(cls, *args, **kwargs):
                called_hooks['pre_delete'] = 1
                
            def on_post_delete(cls, *args, **kwargs):
                called_hooks['post_delete'] = 1
        
        
        Foo.hooks.trigger_pre('create')
        self.assertTrue(called_hooks['pre_create'])
        
        Foo.hooks.trigger_post('create')
        self.assertTrue(called_hooks['post_create'])
        
        Foo.hooks.trigger_pre('update')
        self.assertTrue(called_hooks['pre_update'])
        
        Foo.hooks.trigger_post('update')
        self.assertTrue(called_hooks['post_update'])
        
        Foo.hooks.trigger_pre('delete')
        self.assertTrue(called_hooks['pre_delete'])
        
        Foo.hooks.trigger_post('delete')
        self.assertTrue(called_hooks['post_delete'])
        
        
    def test_multiple_inheritance_fail(self):
        """
        Raises an error when extending more than one Entity
        """
        model = Model()
        
        
        class Foo(model.Entity):
            pass
        
         
        class Bar(model.Entity):
            pass
            
        with self.assertRaises(Exception) as cm:
            class Baz(Foo, Bar):
                pass
                
        self.assertEquals(cm.exception.message, "Cannot extend more than one Entity")
        
        
    def test_get_entity_hierarchy(self):
        """Can get a list including the entity and all its bases in hierarchical order"""
        model = Model()
        
        
        class Foo(model.Entity):
            pass
            
        class Bar(Foo):
            pass
            
        class Baz(Bar):
            pass
            
        self.assertEquals(Baz.hierarchy, [Foo, Bar])
        self.assertEquals(model.Foo.hierarchy, [])
        self.assertEquals(model.Foo.children, [Bar, Baz])
        self.assertEquals(Bar.children, [Baz])
        
        
    def test_inheritance_field_summing(self):
        """A descendant should have it's ancestor's fields as well as its own."""
        model = Model()
        
        class Foo(model.Entity):
            a = Text()
            b = Text()
        
        class Bar(Foo):
            c = Text()
            
        self.assertEquals(set(Bar.fields.keys()), set(['a', 'b', 'c']))
        
        result = Bar.validator.validate({'a':'1','b':'2','c':'3'})
        self.assertEquals(result, {'a':'1','b':'2','c':'3'})
        
        
    def test_visible_fields(self):
        """Has sets for visible and hidden fields"""
        model = Model()
        
        
        class Foo(model.Entity):
            a = Text()
            b = Text()
            c = Text(hidden=True)
            d = Link('Bar')
        
        self.assertEquals(model.Foo.hidden_fields, {'c'})
        self.assertEquals(model.Foo.visible_fields, {'a', 'b', 'd'})
        
        
    def test_embeddable(self):
        """Has sets for embeddable and default embedded references"""
        model = Model()
        
        
        class Foo(model.Entity):
            a = Link('Bar')
            b = Link('Bar', embeddable=True)
            c = Link('Bar', embeddable=True, embed_by_default=False)
        
        self.assertEquals(model.Foo.embeddable, {'b', 'c'})
        self.assertEquals(model.Foo.embed_by_default, {'b'})
        
        
    def test_mixins(self):
        """Can have a list of mixins that add additional fields"""
        model = Model()
        
        
        class Named(model.Entity):
            name = Text()
        
            
        class Foo(model.Entity):
            mixins = (Named,)
            
        foo = Foo()
        self.assertTrue(hasattr(foo, 'name'))
        self.assertEquals(foo.name.__class__, Text)
        
        
    def test_mixin_hooks(self):
        """Mixins can have hooks that are registered on an entity"""
        model = Model()
        
        
        class Fooable(model.Entity):
            
            def on_pre_create(self, fields, *args, **kwargs):
                fields['foo'] = 123
        
                
        class Bar(model.Entity):
            mixins = (Fooable(),)
            
        bar = Bar()
        fields = {}
        bar.hooks.trigger_pre('create', fields)
        self.assertIn('foo', fields)
        self.assertEquals(fields['foo'], 123)
        
        
    def test_inherited_mixin_fields(self):
        """Mixin fields should be inherited"""
        model = Model()
        
        
        class Fooable(object):
            foo = Text()
            
        
        class Barable(object):
            bar = Text()
            
        
        class Thing(model.Entity):
            mixins = (Fooable,)
            
        
        class SpecificThing(Thing):
            mixins = (Barable,)
            
        st = SpecificThing()
        self.assertTrue(hasattr(st, 'foo'))
        self.assertTrue(hasattr(st, 'bar'))
        
        
    def test_inherited_mixin_hooks(self):
        """Mixin hooks should be inherited"""
        model = Model()
        
        
        class Fooable(model.Entity):
            def on_pre_create(self, fields):
                fields['foo'] = 1
                
        
        class Barable(model.Entity):
            def on_pre_create(self, fields):
                fields['bar'] = 1
            
        
        class Thing(model.Entity):
            mixins = (Fooable,)
            
        
        class SpecificThing(Thing):
            mixins = (Barable,)
            
        st = SpecificThing()
        fields = {}
        st.hooks.trigger_pre('create', fields)
        self.assertEquals(fields, {'foo':1, 'bar':1})
        
        
        
class TestModel(unittest.TestCase):
    
    def setUp(self):
        model = Model()
        
    
    def test_unresolvable_link(self):
        """
        Should raise an error if a link can't be resolved
        """
        model = Model()
        
        class Foo(model.Entity):
            bar = Link('Bar')
        
        with self.assertRaises(InvalidModelException):
            model.freeze()
            
            
    def test_foreign_link(self):
        """
        Should raise an error if a link points to an entity that isn't in the model
        """
        model = Model()
        
        class Foo(model.Entity):
            pass
        
        other_model = Model()
        class Bar(other_model.Entity):
            foo = Link(Foo)
            
        with self.assertRaises(InvalidModelException):
            other_model.freeze()
            
            
    def test_pass(self):
        """
        Should do nothing special when initialized with a well-defined model
        """
        model = Model()
        
        class Foo(model.Entity):
            bar = Link('Bar')
            
        class Bar(model.Entity):
            foos = ListOf(Link(Foo))
            
        model.freeze()
        
        
    def test_fail_add_to_frozen(self):
        """
        Can't add an entity to a frozen model
        """
        model = Model()
        
        class Foo(model.Entity):
            pass
            
        model.freeze()
        
        with self.assertRaises(Exception):
            class Bar(model.Entity):
                pass
                
                
    def test_freeze_set_storage(self):
        """
        Freezing a model resolves all links and sets their storage attribute
        """
        model = Model(storage='foo')
        
        class Foo(model.Entity):
            bar = Link('Bar')
            
            
        class Bar(model.Entity):
            pass
            
        model.freeze()
        
        self.assertEquals(Foo.bar.entity, Bar)
        self.assertEquals(Foo.bar.storage, 'foo')
        
        
        
if __name__ == "__main__":
    unittest.main()
