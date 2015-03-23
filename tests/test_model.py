"""
Unit tests for data fields
"""
import unittest
from mock import Mock
from cellardoor.model import *
from cellardoor.storage import Storage


class TestEntity(unittest.TestCase):
    
    def test_reserved_names(self):
        """
        An exception is raised if an entity defines a field that starts with an underscore
        """
        model = Model()
        
        with self.assertRaises(Exception):
            class Foo(model.Entity):
                _stuff = Text()
    
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
        
        
        class Named(object):
            name = Text()
        
            
        class Foo(model.Entity):
            mixins = (Named,)
            
        foo = Foo()
        self.assertTrue(hasattr(foo, 'name'))
        self.assertEquals(foo.name.__class__, Text)
        
        
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
            Foo.get_link('bar')
            
            
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
            Bar.get_link('foo')
            
            
    def test_pass(self):
        """
        Should do nothing special when initialized with a well-defined model
        """
        model = Model(storage=Storage())
        
        class Foo(model.Entity):
            bar = Link('Bar')
            
        class Bar(model.Entity):
            foos = ListOf(Link(Foo))
            
        Foo.get_link('bar')
        Bar.get_link('foos')
        
        
    def test_fail_add_to_frozen(self):
        """
        Can't add an entity to a frozen model
        """
        model = Model(storage=Storage())
        
        class Foo(model.Entity):
            pass
            
        model.freeze()
        
        with self.assertRaises(Exception):
            class Bar(model.Entity):
                pass
                
                
    def test_link_validation_optional(self):
        """
        link validates a None value when the link is optional
        """
        link = Link('foo')
        value = link.validate(None)
        self.assertEquals(value, None)
        
        
    def test_link_validation_unknown(self):
        """
        A validation error is raised if the item referred to by the link doesn't exist.
        """
        link = Link('foo')
        link.model = Mock()
        link.model.storage = Mock()
        link.model.storage.get_by_id = Mock(return_value=None)
        
        with self.assertRaises(ValidationError):
            link.validate('123')
        
        
        
    def test_link_validation_exists(self):
        """
        Link validation returns the original value if the referenced item exists
        """
        link = Link('foo')
        link.model = Mock()
        link.model.storage = Mock()
        link.model.storage.get_by_id = Mock(return_value=True)
        id = '123'
        result = link.validate(id)
        self.assertEquals(result, id)
        
        
    def test_multiple_link(self):
        """
        A link is defined as a multiple link if it is a list of links or a multiple inverse link
        """
        model = Model()
        
        class Foo(model.Entity):
            bar = Link('Bar')
            
            
        class Bar(model.Entity):
            one_foo = Link(Foo)
            list_of_foos = ListOf(Link(Foo))
            inverse_foos = InverseLink(Foo, 'bar')
            
        self.assertEquals(False, Bar.is_multiple_link(Bar.one_foo))
        self.assertEquals(True, Bar.is_multiple_link(Bar.list_of_foos))
        self.assertEquals(True, Bar.is_multiple_link(Bar.inverse_foos))
        
        
    def test_redefine(self):
        """
        Attempting to define an entity that has already been added to a model raises an error
        """
        model = Model()
        
        class Foo(model.Entity):
            pass
            
        with self.assertRaises(Exception):
            class Foo(model.Entity):
                pass
        
        
    def test_repr(self):
        """
        A model has a clear string representation
        """
        model = Model('foo', 'bar')
        self.assertEquals(repr(model), "Model(name='foo', storage='bar')")
        
        
if __name__ == "__main__":
    unittest.main()
