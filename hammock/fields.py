"""
This package provides a simple validation system as well as a number of 
fields and converters. You'll probably find it's usage familiar.

Fields generally perform one task: check that a value meets a certain
specification. Sometimes they also perform a conversion. For instance, a time
field might validate that a value is in one of a number of formats and then
convert the value to, say, a datetime instance or a POSIX timestamp.

This package tries to supply a number of flexible fields but doesn't even
come close to the kitchen sink. Most applications will have their own validation 
requirements and the thinking here is to make it as easy as possible to create 
new fields.

So, creating fields is straightforward. Subclass Field and implement 
the validate() method. That's all that's required. Here is an example that will 
only validate yummy things. Optionally, it will convert to yumminess level::

    class Yummy(Field):
        yumminess = {
            'Pizza': 1.5,
            'Pie': 2.75,
            'Steak': 5.58,
            'Sushi': 14.62,
            'Duck Confit': 28.06
        }
        
        def __init__(self, should_convert=False, **kwargs):
            self.should_convert = should_convert
            super(Yummy, self).__init__(**kwargs)
            
            
        def _validate(self, value):
            if value not in self.yumminess:
                raise ValidationError('Yumminess not known for "%s"' % value)
            
            if self.should_convert:
                return self.yumminess[value]
            
            return value

It's a convention, but not a requirement, to put error values in the class like so::

    class Yummy(Field):
        NOT_YUMMY = "This is not yummy"
        
        def _validate(self, value):
            if not self.is_yummy(value):
                raise ValidationError(self.NOT_YUMMY)

Then we can do things based on the type of error, if we so desire::

    yummy_field = Yummy()
    try:
        yummy_field.validate('Fried Okra')
        print "Fried Okra is yummy!"
    except ValidationError, e:
        if e.message == Yummy.NOT_YUMMY:
            print "Fried Okra is not yummy"
        else:
            print "There is something wront with Fried Okra"

"""

import re
from datetime import datetime

__all__ = [
    'ValidationError',
    'CompoundValidationError',
    'Field',
    'CompoundField',
    'Text',
    'Email',
    'DateTime',
    'Boolean',
    'BoundingBox',
    'LatLng',
    'Enum',
    'TypeOf',
    'URL',
    'OneOf',
    'ListOf',
    'Anything'
]

class ValidationError(Exception):
    """
    This exception is thrown by all fields to indicate that data is invalid::
    
        v = SomeField()
        try:
            v.validate("puppies")
        except ValidationError, e:
            print "Oh no! Something's wrong! %s" % e.message
    """


class CompoundValidationError(ValidationError):
    """
    This exception represents a group of invalid errors. It takes a dict where
    the keys are, presumably, the names of items that were invalid and the values
    are the errors for their respective items::
        
        
        def check_stuff_out(stuff):
            field = SomeField()
            errors = {}
            
            for k,v in stuff.items():
                try:
                    field.validate(v)
                except ValidationError, e:
                    errors[k] = e
            
            if errors:
                raise CompoundValidationError(errors)
    """
    
    def __init__(self, errors):
        self.errors = errors
        super(CompoundValidationError, self).__init__(
            "Some errors were encountered\n" + \
            '\n'.join(["%s: %s" % (k,v) for k,v in errors.items()]))



class Field(object):
    """
    This is the base field class. Don't use it unless you are subclassing to
    create your own field.
    """
    
    def __init__(self, required=False, default=None):
        self.required = required
        self.default = default
        
    def validate(self, value):
        if value is None:
            if self.required:
                raise ValidationError, "This field is required."
            value = self.default
        
        return self._validate(value)
        
    def _validate(self, value):
        raise NotImplementedError


class CompoundField(Field):
    """
    Validates a a dict of `key => field`::
    
        v = CompoundField(foo=Text(), bar=TypeOf(int))
        v.validate({'foo':'oof', 'bar':23}) # ok
        v.validate(5) # nope
        v.validate('foo':'gobot', 'bar':'pizza') # nope
        
        # unspecified keys are filtered
        v.validate({'foo': 'a', 'goo': 'b', 'bar':17})
        # ok -> {'foo': 'a', 'bar':17}
        
        # Fields are optional by default
        v = CompoundField(foo=Text(), bar=TypeOf(int, default=8))
        v.validate({'foo':'ice cream'}) # -> {'foo':'ice cream', 'bar': 8}
    """
    NOT_A_DICT = "Not a dict"
    
    def __init__(self, **kwargs):
        keys = ['required', 'default']
        newkwargs = {}
        
        for k in keys:
            if k in kwargs:
                newkwargs[k] = kwargs.pop(k)
        
        Field.__init__(self, **newkwargs)
        self.fields = kwargs
        
        
    def _validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError(self.NOT_A_DICT)
        
        validated = {}
        errors = {}
        
        for k,v in self.fields.items():
            try:
                validated[k] = v.validate(value.get(k))
            except ValidationError, e:
                errors[k] = e
        
        if errors:
            raise CompoundValidationError(errors)
        
        return validated


class Text(Field):
    """
    Passes text, optionally checking length::
    
        v = Text(minlength=2,maxlength=7)
        v.validate("foo") # ok
        v.validate(23) # oops
        v.validate("apron hats") # oops
        v.validate("f") # oops
    """
    NOT_TEXT = 'Expected some text.'
    TOO_SHORT = 'This text is too short.'
    TOO_LONG = 'This text is too long.'
    
    def __init__(self, minlength=None, maxlength=None, **kwargs):
        self.minlength = minlength
        self.maxlength = maxlength
        super(Text, self).__init__(**kwargs)
        
    def _validate(self, value):
        if not isinstance(value, basestring):
            raise ValidationError(self.NOT_TEXT)
            
        if self.minlength is not None and len(value) < self.minlength:
            raise ValidationError(self.TOO_SHORT)
            
        if self.maxlength is not None and len(value) > self.maxlength:
            raise ValidationError(self.TOO_LONG)
            
        return value


class Email(Text):
    """
    Passes email addresses that meet the guidelines in `RFC 3696 <http://tools.ietf.org/html/rfc3696>`_::
    
        v = Email()
        v.validate("foo@example.com") # ok
        v.validate("foo.bar_^&!baz@example.com") # ok
        v.validate("@example.com") # oops!
    """
    NOT_EMAIL = "Invalid email address"
    pattern = re.compile("^((\".+\")|((\\\.))|([\d\w\!#\$%&'\*\+\-/=\?\^_`\{\|\}~]))((\"[^@]+\")|(\\\.)|([\d\w\!#\$%&'\*\+\-/=\?\^_`\.\{\|\}~]))*@[a-zA-Z0-9]+([a-zA-Z0-9\-][a-zA-Z0-9]+)?(\.[a-zA-Z0-9]+([a-zA-Z0-9\-][a-zA-Z0-9]+)?)+\.?$")
    
    def _validate(self, value):
        value = super(Email, self)._validate(value)
        
        if not isinstance(value, basestring):
            raise ValidationError(self.NOT_EMAIL)
        if not self.pattern.match(value):
            raise ValidationError(self.NOT_EMAIL)
        return value


try:
    import timelib
    strtodatetime = timelib.strtodatetime
except ImportError:
    strtodatetime = None

try:
    from dateutil import parser as date_parser
    parsedate = date_parser.parse
except ImportError:
    parsedate = None

class DateTime(Field):
    """
    Validates many representations of date & time and converts to datetime.datetime.
    It will use `timelib <http://pypi.python.org/pypi/timelib/>`_ if available,
    next it will try `dateutil.parser <http://labix.org/python-dateutil>`_. If neither
    is found, it will use :func:`datetime.strptime` with some predefined format string.
    Int or float timestamps will also be accepted and converted::
    
        # assuming we have timelib
        v = DateTime()
        v.validate("today") # datetime.datetime(2011, 9, 17, 0, 0, 0)
        v.validate("12:06am") # datetime.datetime(2011, 9, 17, 0, 6)
        v.validate(datetime.now()) # datetime.datetime(2011, 9, 17, 0, 7)
        v.validate(1316232496.342259) # datetime.datetime(2011, 9, 17, 4, 8, 16, 342259)
        v.validate("baloon torches") # oops!
    """
    NOT_DATE = "Unrecognized date format"
    
    def __init__(self, default_format="%x %X", use_timelib=True, 
            use_dateutil=True, **kwargs):
        super(DateTime, self).__init__(**kwargs)
        self.default_format = default_format
        self.use_timelib = use_timelib
        self.use_dateutil = use_dateutil
        
        
    def _validate(self, value):
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, int) or isinstance(value, float):
            try:
                return datetime.utcfromtimestamp(value)
            except:
                raise ValidationError(self.NOT_DATE)
        
        if not isinstance(value, basestring):
            raise ValidationError, "Note a date or time"
        
        if self.use_timelib and strtodatetime:
            try:
                return strtodatetime(value)
            except:
                raise ValidationError(self.NOT_DATE)
        
        if self.use_dateutil and parsedate:
            try:
                return parsedate(value)
            except:
                raise ValidationError(self.NOT_DATE)
        
        try:
            return datetime.strptime(value, self.default_format)
        except:
            raise ValidationError(self.NOT_DATE)
            
            
class Boolean(Field):
    """
    Passes and converts most representations of True and False::
        
        b = Bool()
        b.validate("true") # True
        b.validate(1) # True
        b.validate("yes") # True
        b.validate(True) # True
        b.validate("false") # False, etc.
        
    """
    NOT_BOOL = "Not a boolean"
    
    
    def _validate(self, value):
        if isinstance(value, basestring):
            v = value.lower()
            if v in ["true", "1", "yes"]:
                return True
            elif v in ["false", "0", "no"]:
                return False
            else:
                raise ValidationError(self.NOT_BOOL)
        elif isinstance(value, int):
            if value == 1:
                return True
            elif value == 0:
                return False
            else:
                raise ValidationError(self.NOT_BOOL)
        elif isinstance(value, bool):
            return value
        raise ValidationError(self.NOT_BOOL)
        
        
class BoundingBox(Field):
    """
    Passes a geographical bounding box of the form SWNE, e.g., 37.73,-122.48,37.78,-122.37.
    It will accept a list or a comma-separated string::
    
        v = BoundingBox()
        b.validate([42.75804,-85.0031, 42.76409, -84.9861]) # ok
        b.validate("42.75804,-85.0031, 42.76409, -84.9861") # -> [42.75804,-85.0031, 42.76409, -84.9861]
    """
    VALUES_OUT_OF_RANGE = "All values must be numbers in the range -180.0 to 180.0"
    WRONG_SIZE = "A bounding box must have 4 values"
    NOT_STRING_OR_LIST = "Expected a comma-separated list of values or a list or tuple object."
    
    def _validate(self, value):
        if not isinstance(value, (list, tuple)):
            if isinstance(value, basestring):
                value = [v.strip() for v in value.split(',')]
            else:
                raise ValidationError(self.NOT_STRING_OR_LIST)
        
        if len(value) != 4:
            raise ValidationError(self.WRONG_SIZE)
            
        try:
            value = [float(v) for v in value]
        except ValueError:
            raise ValidationError(self.VALUES_OUT_OF_RANGE)
        
        for v in value:
            if not (-180.0 <= v <= 180.0):
                raise ValidationError(self.VALUES_OUT_OF_RANGE)
        
        return tuple(value)
        
        
class LatLng(Field):
    """
    Passes a geographical point in for form of a list, tuple or comma-separated string::
    
        v = LatLng()
        v.validate("42.76066, -84.9929") # ok -> (42.76066, -84.9929)
        v.validate((42.76066, -84.9929)) # ok
        v.validate("234,56756.453") # oops
    """
    VALUES_OUT_OF_RANGE = "All values must be numbers in the range -180.0 to 180.0"
    WRONG_SIZE = "A point must have 2 values"
    NOT_STRING_OR_LIST = "Expected a comma-separated list of values or a list or tuple object."
    
    def _validate(self, value):
        if not isinstance(value, (list, tuple)):
            if not isinstance(value, basestring):
                raise ValidationError(self.NOT_STRING_OR_LIST)
            value = [v.strip() for v in value.split(",")]
        
        if len(value) != 2:
            raise ValidationError(self.WRONG_SIZE)
        
        try:
            value = [float(v) for v in value]
        except ValueError:
            raise ValidationError(self.VALUES_OUT_OF_RANGE)
        
        for v in value:
            if not (-180.0 <= v <= 180.0):
                raise ValidationError(self.VALUES_OUT_OF_RANGE)
        
        return tuple(value)
        
        
class Enum(Field):
    """
    Passes anything that evaluates equal to one of a list of values::
    
        v = Enum('a', 'b', 'c')
        v.validate('a') # ok
        v.validate('d') # nope!
    """
    NOT_IN_LIST = "Not in the list"
    
    def __init__(self, *values, **kwargs):
        super(Enum, self).__init__(**kwargs)
        self.values = values
    
    
    def _validate(self, value):
        if value in self.values:
            return value
        raise ValidationError(self.NOT_IN_LIST)
        
        
class TypeOf(Field):
    """
    Passes any value of a specified type::
    
        v = TypeOf(float)
        v.validate(0.4) # ok
        v.validate(1) # nope
        
        # more than one type is ok too
        v = TypeOf(int, float, complex)
        v.validate(5) # ok
        v.validate(5.5) # ok
        v.validate(complex(5,5)) # ok
    """
    
    def __init__(self, *types, **kwargs):
        super(TypeOf, self).__init__(**kwargs)
        self.types = types
        
        
    def _validate(self, value):
        if not isinstance(value, self.types):
            raise ValidationError, "Not of type '%s'" % (self.types,)
        return value
        
        
class URL(Text):
    """
    Passes a URL using guidelines from RFC 3696::
        
        v = URL()
        v.validate('http://www.example.com') # ok
        v.validate('https://www.example.com:8000/foo/bar?smelly_ones=true#dsfg') # ok
        v.validate('http://www.example.com/foo;foo') # nope
        
        # You can also set which schemes to match
        v = URL(schemes=('gopher',))
        v.validate('gopher://example.com/') # ok
        v.validate('http://example.com/') # nope!
    
    Regex from http://daringfireball.net/2010/07/improved_regex_for_matching_urls.
    """
    NOT_A_URL = "Not a URL"
    
    def __init__(self, **kwargs):
        super(URL, self).__init__(**kwargs)
        self.pattern = re.compile('((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xc2\xab\xc2\xbb\xe2\x80\x9c\xe2\x80\x9d\xe2\x80\x98\xe2\x80\x99]))')
        
        
    def _validate(self, value):
        value = super(URL, self)._validate(value)
        
        if not self.pattern.match(value):
            raise ValidationError(self.NOT_A_URL)
        return value
        
        
class OneOf(Field):
    """
    Passes values that pass one of a list of fields::
    
        v = OneOf(URL(), Enum('a', 'b'))
        v.validate('b') # ok
        v.validate('http://www.example.com') # ok
        v.validate(23) # nope
    """
    
    def __init__(self, *fields, **kwargs):
        super(OneOf, self).__init__(**kwargs)
        self.fields = fields
        
        
    def _validate(self, value):
        is_valid = False
        
        for v in self.fields:
            try:
                v.validate(value)
                is_valid = True
                break
            except ValidationError:
                pass
        
        if is_valid:
            return value
            
        raise ValidationError("Didn't match any fields")
        
        
class ListOf(Field):
    """
    Passes a list of values that pass a field::
    
        v = ListOf(TypeOf(int))
        v.validate([1,2,3]) # ok
        v.validate([1,2,"3"]) # nope
        v.validate(1) # nope
    """
    NOT_A_LIST = "Not a list"
    
    def __init__(self, field, **kwargs):
        super(ListOf, self).__init__(**kwargs)
        self.field = field
        
        
    def validate(self, values):
        if not isinstance(values, list):
            raise ValidationError(self.NOT_A_LIST)
        
        for v in values:
            self.field.validate(v)
        
        return values
        
        
class Anything(Field):
    """
    Passes anything
    """
    
    def _validate(self, value):
        return value
        
        
        
class Many(Field):
    pass
    
    
class One(Field):
    pass
