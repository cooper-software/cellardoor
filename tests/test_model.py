"""
Unit tests for data fields
"""
import unittest
from hammock.model import *
from datetime import datetime
import time


class TestAbstractField(unittest.TestCase):
    
    def test_field_abstract(self):
        """
        Shouldn't be able to use base Field as a field
        """
        field = Field()
        self.assertRaises(NotImplementedError, field.validate, 23)
        
        
class TestText(unittest.TestCase):
        
    def test_not_text(self):
        """
        Should raise ValidationError for anything but a string
        """
        field = Text()
        self.assertRaises(ValidationError, field.validate, 23)
        
        
    def test_text(self):
        """
        Should not raise ValidationError for text
        """
        field = Text()
        try:
            field.validate("foo")
        except ValidationError:
            self.fail("Text.validate() raised ValidationError for a string")
            
            
    def test_minlength_success(self):
        """
        Should not raise ValidationError if a string is longer than minlength.
        """
        test_string = "foofoo"
        field = Text(minlength=len(test_string)-1)
        
        try:
            field.validate(test_string)
        except ValidationError:
            self.fail("Text.validate(minlength=%d) raised ValidationError for a string of length %d" %(
                len(test_string)-1, len(test_string)))
            
            
    def test_minlength_fail(self):
        """
        Should raise ValidationError if a string is shorter than minlength.
        """
        test_string = "foofoo"
        field = Text(minlength=len(test_string)+1)
        self.assertRaises(ValidationError, field.validate, test_string)
        
        
    def test_maxlength_success(self):
        """
        Should not raise ValidationError if a string's length is less than or equal to maxlength
        """
        test_string = "foofoo"
        test_string_len = len(test_string)
        field = Text(maxlength=test_string_len)
        
        try:
            field.validate(test_string)
        except ValidationError:
            self.fail("Text.validate(maxlength=%d) raised ValidationError for a string of length %d" %(
                test_string_len, test_string_len))
            
            
        field = Text(maxlength=test_string_len+1)
        
        try:
            field.validate(test_string)
        except ValidationError:
            self.fail("Text.validate(maxlength=%d) raised ValidationError for a string of length %d" %(
                test_string_len+1, test_string_len))
            
            
    def test_maxlength_fail(self):
        """
        Should raise ValidationError if a string is longer than maxlength
        """
        test_string = "foofoo"
        field = Text(maxlength=len(test_string)-1)
        self.assertRaises(ValidationError, field.validate, test_string)
        
        
    def test_return_value(self):
        """
        Should always return the input value
        """
        string = "foobarbaz"
        field = Text(minlength=1,maxlength=23)
        self.assertEqual(string, field.validate(string))
        
        
    def test_required_fail(self):
        """
        Should fail if field is required and passed an empty string
        """
        field = Text(required=True)
        
        with self.assertRaises(ValidationError):
            field.validate('')
            
            
    def test_regex_fail(self):
        """
        Should fail if the input value doesn't match the field's regex
        """
        field = Text(regex=r'^foo$')
        
        with self.assertRaises(ValidationError):
            field.validate('bar')
            
            
    def test_regex_pass(self):
        """
        Should pass if the input value matches the field's regex
        """
        field = Text(regex=r'^foo$')
        validated_value = field.validate('foo')
        self.assertEquals(validated_value, 'foo')
        
        
class TestEmail(unittest.TestCase):
    
    def test_fail(self):
        """
        Should raise ValidationError on things that aren't email addresses
        """
        field = Email()
        not_emails = [
            23,
            "foo",
            "@foo.com"
        ]
        
        for not_email in not_emails:
            self.assertRaises(ValidationError, field.validate, not_email)
        
        
    def test_pass(self):
        """
        Should accept addresses that meet the guidelines in RFC 3696
        """
        emails = [
            'foo@example.com',
            'a@b.c',
            'foo@exa.amp.le.com',
            'foo_bar@example.com.',
            'foo.bar@example.com',
            'f!o#o$b%a&r\'b*a+z-b/a=n?g^b_i`f.b{o|p}~@example.com',
            '"some white space"@example.com',
            '\@fo"   "\//o@example.com'
        ]
        
        field = Email()
        
        for email in emails:
            try:
                self.assertEquals(email, field.validate(email))
            except ValidationError:
                self.fail('Failed to accept %s' % email)
        
        
class TestDateTime(unittest.TestCase):
    
    def test_fail(self):
        """
        Should raise invalid for things that aren't dates and times
        """
        field = DateTime()
        not_datetimes = [
            "santa claus",
            "the cure is wednesday",
            "324"
        ]
        
        for not_datetime in not_datetimes:
            self.assertRaises(ValidationError, field.validate, not_datetime)
        
        
    def test_simple(self):
        """
        Should parse dates in the default format and return them as datetime objects.
        """
        field = DateTime(default_format="%x")
        bday = datetime(1982, 9, 6)
        
        try:
            self.assertEqual(bday, field.validate('9/6/82'))
        except ValidationError:
            self.fail('Failed to validate 9/6/82 with format %x')
        
        
    def test_timelib(self):
        """
        If timelib is installed, should be able to parse stuff like "today"
        """
        try:
            import timelib
        except ImportError:
            print "timelib is not installed, skipping timelib test for DateTime field"
            return
        
        field = DateTime(use_timelib=True, use_dateutil=False)
        today = datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)
        
        self.assertEqual(today, field.validate("today"))
        
        
    def test_dateutil(self):
        """
        If dateutil is installed, should be able to parse formats other than the default
        """
        try:
            import dateutil
        except ImportError:
            print "dateutil is not installed, skipping dateutil test for DateTime field"
            return
        
        field = DateTime(default_format="%d", use_timelib=False, use_dateutil=True)
        bday = datetime(1982,9,6)
        
        self.assertEqual(bday, field.validate('9/6/82'))
            
            
    def test_reflexive(self):
        """
        Should pass and return a datetime.datetime instance.
        """
        field = DateTime()
        now = datetime.now()
        
        try:
            self.assertEquals(now, field.validate(now))
        except ValidationError:
            self.fail("Failed to pass a datetime.datetime instance")
            
            
    def test_timestamp(self):
        """
        Should pass both int and float timestamps and convert to utc datetime
        """
        field = DateTime()
        now = time.time()
        now_date = datetime.utcfromtimestamp(now)
        
        try:
            self.assertEquals(now_date, field.validate(now))
        except ValidationError:
            self.fail("Failed to pass a float timestamp")
            
        now = int(now)
        now_date = datetime.utcfromtimestamp(now)
        
        try:
            self.assertEquals(now_date, field.validate(now))
        except ValidationError:
            self.fail("Failed to pass an int timestamp")
        
        
class TestBoolean(unittest.TestCase):
    
    def test_fail(self):
        """
        Should raise ValidationError for things that don't represent booleans
        """
        not_bools = [
            "maybe",
            67,
            dict
        ]
        
        field = Boolean()
        
        for not_bool in not_bools:
            self.assertRaises(ValidationError, field.validate, not_bool)
        
        
    def test_falses(self):
        """
        Should pass and convert several represenations of False
        """
        falses = [
            False,
            0,
            "0",
            "false",
            "FALSE",
            "fAlSe",
            "no",
            "No"
        ]
        
        field = Boolean()
        
        for false in falses:
            try:
                self.assertEqual(False, field.validate(false))
            except ValidationError:
                self.fail("Didn't pass '%s'" % false)
        
        
    def test_falses(self):
        """
        Should pass and convert several represenations of True
        """
        trues = [
            True,
            1,
            "1",
            "true",
            "TRUE",
            "TruE",
            "yes",
            "yEs"
        ]
        
        field = Boolean()
        
        for true in trues:
            try:
                self.assertEqual(True, field.validate(true))
            except ValidationError:
                self.fail("Didn't pass '%s'" % true)
        
        
        
class TestBoundingBox(unittest.TestCase):
    
    def test_fail(self):
        """
        Shouldn't pass things that aren't a bounding box.
        """
        not_bboxes = [
            "fred",
            (1,3,4),
            ["apples", 42, 24, 6],
            (1,181,3,-300),
            348.345
        ]
        field = BoundingBox()
        
        for not_bbox in not_bboxes:
            try:
                field.validate(not_bbox)
                self.fail("Passed '%s'" % (not_bbox,))
            except ValidationError:
                pass
        
        
    def test_list(self):
        """
        Should pass a list or tuple
        """
        box = [42.75804,-85.0031, 42.76409, -84.9861]
        field = BoundingBox()
        
        try:
            field.validate(box)
        except ValidationError:
            self.fail("Failed '%s'", box)
            
        box = tuple(box)
        
        try:
            field.validate(box)
        except ValidationError:
            self.fail("Failed '%s'", box)
        
        
    def test_string(self):
        """
        Should pass a comma-separated string and convert to a tuple
        """
        box = (42.75804,-85.0031, 42.76409, -84.9861)
        str_box = ",".join([str(b) for b in box])
        field = BoundingBox()
        
        try:
            self.assertEqual(box, field.validate(str_box))
        except ValidationError:
            self.fail("Failed '%s'", str_box)
        
        
class TestLatLng(unittest.TestCase):
    
    def test_fail(self):
        """
        Should throw ValidationError for things that aren't a geographic point
        """
        not_latlngs = [
            14,
            "the whole earf",
            {'foo': 'bar'},
            (181,-181)
        ]
        
        field = LatLng()
        
        for not_latlng in not_latlngs:
            try:
                field.validate(not_latlng)
                self.fail("Passed %s" % (not_latlng,))
            except ValidationError:
                pass
            
            
    def test_pass(self):
        """
        Should pass a list, tuple or comma-separated string.
        """
        latlngs = [
            "42.76066, -84.9929",
            (42.76066, -84.9929),
            [42.76066, -84.9929]
        ]
        
        field = LatLng()
        
        for latlng in latlngs:
            try:
                field.validate(latlng)
            except ValidationError:
                self.fail("Failed to pass %s" % latlng)
        
        
    def test_return_value(self):
        """
        Should always return a 2-tuple of floats
        """
        latlng = (42.76066, -84.9929)
        latlngs = [list(latlng), "%s,%s" % latlng]
        
        field = LatLng()
        
        for l in latlngs:
            self.assertEqual(latlng, field.validate(l))
        
        
class TestEnum(unittest.TestCase):
    
    def test_fail(self):
        """
        Shouldn't pass anything not in the defined list
        """
        values = [5, "atilla the hun", unicode]
        wrong = [8, "ivan the terrible", str]
        
        field = Enum(*values)
        
        for w in wrong:
            self.assertRaises(ValidationError, field.validate, w)
            
            
    def test_pass(self):
        """
        Should pass anything in the defined list
        """
        values = [5, "atilla the hun", unicode]
        
        field = Enum(*values)
        
        for value in values:
            try:
                self.assertEqual(value, field.validate(value))
            except ValidationError:
                self.fail("Didn't pass %s" % value)
        
        
class TestTypeOf(unittest.TestCase):
    
    def test_fail(self):
        """
        Shouldn't pass values of a type not specified
        """
        field = TypeOf(int)
        self.assertRaises(ValidationError, field.validate, "Hi, hungry?")
        
        
    def test_pass(self):
        """
        Should pass values of the specified type
        """
        field = TypeOf(basestring)
        value = u"foo"
        
        try:
            self.assertEqual(value, field.validate(value))
        except ValidationError:
            self.fail("Didn't pass value of specified type")
        
        
class TestURL(unittest.TestCase):
    
    def test_fail(self):
        """
        Don't pass things that aren't URLs.
        """
        not_urls = ["snipe", u'\xe2\x99\xa5', 777]
        field = URL()
        
        for not_url in not_urls:
            self.assertRaises(ValidationError, field.validate, not_url)
        
        
    def test_pass(self):
        """
        Should pass URLs with the specified schemes.
        """
        urls = [
            'http://example.com',
            'foo://example.com./',
            'http://example.com/foo/bar?baz=goo&snoo=snazz#help',
            'http://127.0.0.1',
            'bar://127.0.0.1:80',
            'http://foo:123/',
            'http://foo:bar@baz:123'
        ]
        field = URL()
        
        for url in urls:
            try:
                self.assertEqual(url, field.validate(url))
            except ValidationError:
                self.fail("Didn't pass '%s'" % url)
        
        
class TestOneOf(unittest.TestCase):
    
    def test_fail(self):
        """
        Should not pass things that don't pass at least one field.
        """
        bads = [
            "snooze button",
            50
        ]
        field = OneOf(Email(), TypeOf(float))
        
        for bad in bads:
            self.assertRaises(ValidationError, field.validate, bad)
            
            
    def test_pass(self):
        """
        Should pass anything that matches any of the fields
        """
        goods = [23, 3.1459, "batman", 16]
        field = OneOf(TypeOf(int), Enum(3.1459, "pie", "batman"))
        
        for good in goods:
            try:
                self.assertEqual(good, field.validate(good))
            except ValidationError:
                self.fail("Failed to pass '%s'" % good)
        
        
class TestListOf(unittest.TestCase):
    
    def test_fail(self):
        """
        Shouldn't pass a list of things that don't pass the field or things
        that aren't lists.
        """
        bads = [23, [23,24,25]]
        field = ListOf(TypeOf(basestring))
        
        for bad in bads:
            self.assertRaises(ValidationError, field.validate, bad)
            
            
    def test_pass(self):
        """
        Should pass a list of things that pass the field
        """
        goods = [
            ['a', 15, 'pointy hat'],
            [5],
            ['pancakes', 'alpha centauri', 9]
        ]
        
        field = ListOf(TypeOf(basestring, int))
        
        for good in goods:
            try:
                self.assertEqual(good, field.validate(good))
            except ValidationError:
                self.fail("Failed to pass '%s'", good)
                
                
    def test_required_fail(self):
        """
        Should fail if required and passed an empty list
        """
        field = ListOf(Anything(), required=True)
        
        with self.assertRaises(ValidationError):
            field.validate([])
        
        
class TestCompoundField(unittest.TestCase):
    
    def test_fail(self):
        """
        Shouldn't pass anything that isn't a dict with specified keys and
        validated values.
        """
        bads = [
            {
                5: "6",
                7: "8"
            },
            {
                "hoodo": Text(),
                "we": "appreciate" 
            }
        ]
        
        field = Compound(
            do = Text(required=True),
            we = Text()
        )
        
        for bad in bads:
            self.assertRaises(CompoundValidationError, field.validate, bad)
            
        self.assertRaises(ValidationError, field.validate, "not a dict")
        
        
    def test_pass(self):
        """
        Should pass dicts with specified keys and validated values. Should 
        also return a dict with converted values.
        """
        goods = [
            ({'foo':'bar', 'baz':23}, {'foo':'bar', 'baz':23}),
            ({'foo':'bar'}, {'foo':'bar', 'baz':5.5})
        ]
        
        field = Compound(foo=Text(), baz=TypeOf(int, float, default=5.5))
        
        for good_in, good_out in goods:
            try:
                self.assertEqual(good_out, field.validate(good_in))
            except ValidationError:
                self.fail("Failed to pass %s" % good_in)
                
                
    def test_leave_optionals_out(self):
        """
        Should not set optional values if they are not present in the provided fields.
        """
        field = Compound(foo=Text(), bar=Text())
        result = field.validate({'foo':'123'})
        self.assertEquals(result, {'foo':'123'})
        
        
    def test_can_turn_off_required(self):
        """
        Should be able to turn off enforcement of required fields
        """
        field = Compound(bar=Text(required=True), baz=Text())
        obj = {'baz':'y'}
        result = field.validate(obj, enforce_required=False)
        self.assertEquals(result, obj)
        
        
        
class TestAnything(unittest.TestCase):
    
    def test_pass(self):
        """
        Should pass anything
        """
        field = Anything()
        anythings = ["foo", 7, Anything(), unittest]
        
        for anything in anythings:
            try:
                self.assertEqual(anything, field.validate(anything))
            except ValidationError:
                self.fail('Failed something')
                
                
class TestOne(unittest.TestCase):
    
    def test_fail_bad_value(self):
        """
        Should fail if passed anything but an instance of the specified entity
        """
        
        class Foo(Entity):
            name = Text()
        
        field = One(Foo)
        
        with self.assertRaises(ValidationError):
            field.validate(123)
            
            
    def test_fail_not_ready(self):
        """
        Should raise an error if attempting to validate before an entity is set
        """
        
        field = One('Foo')
        
        class Foo(Entity):
            name = Text()
        
        with self.assertRaises(Exception):
            field.validate(Foo())
            
            
    def test_fail_incorrect_entity(self):
        """
        Should raise an error if passed an incorrect entity type
        """
        
        class Foo(Entity):
            pass
            
            
        class Bar(Entity):
            pass
            
        field = One(Foo)
        
        with self.assertRaises(ValidationError):
            field.validate(Bar())
            
            
    def test_pass(self):
        """
        Should pass an instance of the specified entity
        """
        
        class Foo(Entity):
            pass
        
        field = One(Foo)
        foo = Foo()
        validated_foo = field.validate(foo)
        self.assertEquals(validated_foo, foo)
        
        
class TestMany(unittest.TestCase):
    
    def test_fail_bad_value(self):
        """
        Should fail if passed anything but a list of instances of the specified entity
        """
        
        class Foo(Entity):
            name = Text()
        
        field = Many(Foo)
        
        with self.assertRaises(ValidationError):
            field.validate(123)
            
            
    def test_fail_not_ready(self):
        """
        Should raise an error if attempting to validate before an entity is set
        """
        
        field = Many('Foo')
        
        class Foo(Entity):
            name = Text()
        
        with self.assertRaises(Exception):
            field.validate([Foo()])
            
            
    def test_fail_incorrect_entity(self):
        """
        Should raise an error if passed an incorrect entity type
        """
        
        class Foo(Entity):
            pass
            
            
        class Bar(Entity):
            pass
            
        field = Many(Foo)
        
        with self.assertRaises(ValidationError):
            field.validate([Bar()])
            
            
    def test_pass(self):
        """
        Should pass a list of instances of the specified entity
        """
        
        class Foo(Entity):
            pass
        
        field = Many(Foo)
        foo = Foo()
        validated_foo = field.validate([foo])
        self.assertEquals(validated_foo, [foo])


class TestEntity(unittest.TestCase):
    
    def test_can_validate(self):
        """
        Should validate against a compound validator of its field attributes.
        """
        class Foo(Entity):
            bar = Text(required=True)
            baz = Text(maxlength=10)
        
        with self.assertRaises(CompoundValidationError):
            Foo.validate({'baz':'x'*11})
        
        obj = {'bar':'x', 'baz':'y'}
        result = Foo.validate(obj)
        self.assertEquals(result, obj)
        
        
    def test_can_turn_off_required(self):
        """
        Should be able to turn off enforcement of required fields
        """
        #class Foo(Entity):
        #    bar = Text(required=True)
        #    baz = Text()
        #
        #obj = {'baz':'y'}
        #result = Foo.validate(obj, enforce_required=False)
        #self.assertEquals(result, obj)
        
        
        
class TestModel(unittest.TestCase):
    
    def test_unresolvable_link(self):
        """
        Should raise an error if a link can't be resolved
        """
        
        class Foo(Entity):
            bar = One('Bar')
        
        with self.assertRaises(Exception):
            model = Model('test', [Foo])
            
            
    def test_foreign_link(self):
        """
        Should raise an error if a link points to an entity that isn't in the model
        """
        class Foo(Entity):
            pass
            
        class Bar(Entity):
            foo = One(Foo)
            
        with self.assertRaises(Exception):
            model = Model('test', [Bar])
            
            
    def test_pass(self):
        """
        Should do nothing special when initialized with a well-defined model
        """
        
        class Foo(Entity):
            bar = One('Bar')
            
            
        class Bar(Entity):
            foos = Many(Foo)
            
            
        model = Model('test', [Foo, Bar])
        self.assertTrue(model.has_entity(Foo))
        self.assertTrue(model.has_entity(Bar))
        
        
        
if __name__ == "__main__":
    unittest.main()
