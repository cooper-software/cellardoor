import re
from datetime import datetime
from  .events import EventManager

__all__ = [
    'ValidationError',
    'CompoundValidationError',
    'Field',
    'Entity',
    'EntityMixin',
    'Timestamped',
    'Compound',
    'Text',
    'HTML',
    'Email',
    'DateTime',
    'Boolean',
    'Range',
    'Float',
    'Integer',
    'BoundingBox',
    'LatLng',
    'Enum',
    'TypeOf',
    'URL',
    'OneOf',
    'ListOf',
    'Anything',
    'Reference',
    'Link',
    'Model'
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
    
    def __init__(self, required=False, default=None, hidden=False, unique=False, help=None):
        self.required = required
        self.default = default
        self.hidden = hidden
        self.unique = unique
        self.help = help
        
    def validate(self, value):
        if value is None:
            if self.required:
                raise ValidationError, "This field is required."
            return self.default
        
        return self._validate(value)
        
    def _validate(self, value):
        raise NotImplementedError
                


class Text(Field):
    """
    Passes text, optionally checking length::
    
        v = Text(minlength=2,maxlength=7)
        v.validate("foo") # ok
        v.validate(23) # oops
        v.validate("apron hats") # oops
        v.validate("f") # oops
    """
    NOT_TEXT = 'Expected a text value.'
    TOO_SHORT = 'This text is too short.'
    TOO_LONG = 'This text is too long.'
    REQUIRED = 'Expected a text value.'
    NO_REGEX_MATCH = 'Does not match regex.'
    
    def __init__(self, minlength=None, maxlength=None, regex=None, **kwargs):
        self.minlength = minlength
        self.maxlength = maxlength
        self.regex = re.compile(regex) if regex else None
        super(Text, self).__init__(**kwargs)
        
    def _validate(self, value):
        if not isinstance(value, basestring):
            raise ValidationError(self.NOT_TEXT)
        
        if self.required and len(value) == 0:
            raise ValidationError(self.REQUIRED)
            
        if self.minlength is not None and len(value) < self.minlength:
            raise ValidationError(self.TOO_SHORT)
            
        if self.maxlength is not None and len(value) > self.maxlength:
            raise ValidationError(self.TOO_LONG)
            
        if self.regex is not None and not self.regex.search(value):
            raise ValidationError(self.NO_REGEX_MATCH)
            
        return value
        
        
class HTML(Text):
    pass


class Email(Text):
    """
    Passes email addresses that meet the guidelines in `RFC 3696 <http://tools.ietf.org/html/rfc3696>`_::
    
        v = Email()
        v.validate("foo@example.com") # ok
        v.validate("foo.bar_^&!baz@example.com") # ok
        v.validate("@example.com") # oops!
    """
    NO_REGEX_MATCH = "Invalid email address"
    
    def __init__(self, *args, **kwargs):
        super(Email, self).__init__(
            regex="^((\".+\")|((\\\.))|([\d\w\!#\$%&'\*\+\-/=\?\^_`\{\|\}~]))((\"[^@]+\")|(\\\.)|([\d\w\!#\$%&'\*\+\-/=\?\^_`\.\{\|\}~]))*@[a-zA-Z0-9]+([a-zA-Z0-9\-][a-zA-Z0-9]+)?(\.[a-zA-Z0-9]+([a-zA-Z0-9\-][a-zA-Z0-9]+)?)+\.?$",
            *args, **kwargs)


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
        
        
class Range(Field):
    
    TOO_BIG = "Exceeds the maximum value of %s."
    TOO_SMALL = "Smaller than the minimum value of %s."
    
    def __init__(self, min=None, max=None, *args, **kwargs):
        self.min = min
        self.max = max
        super(Range, self).__init__(*args, **kwargs)
        
        
    def _validate(self, value):
        if self.min and value < self.min:
            raise ValidationError(self.TOO_SMALL % self.str_value(self.min))
        if self.max and self.max < value:
            raise ValidationError(self.TOO_BIG % self.str_value(self.max))
            
            
    def str_value(self, value):
        raise NotImplementedError
        
        
class Float(Range):
    """
    Passes a floating point number.
    
        field = Float()
        field.validate(13) # ok
        field.validate(13.31) # ok
        field.validate('13') # ok -> 13.0
        field.validate('13.31e-4') # -> 0.001331
    """
    
    NOT_A_FLOAT = "Expected a real number."
    
    def _validate(self, value):
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(self.NOT_A_FLOAT)
            
        return super(Float, self)._validate(value)
        
    def str_value(self, value):
        return '%.2f' % value
        
        
        
class Integer(Range):
    """
    Passes an integer.
    
        field = Integer()
        field.validate(13) # ok
        field.validate('13') # ok -> 13
    """
    
    NOT_AN_INTEGER = "Expected an integer."
    
    def _validate(self, value):
        if isinstance(value, float):
            raise ValidationError(self.NOT_AN_INTEGER)
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(self.NOT_AN_INTEGER)
        
        return super(Integer, self)._validate(value)
        
    def str_value(self, value):
        return '%d' % value
        
        
        
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
    NO_REGEX_MATCH = "Not a URL"
    
    def __init__(self, **kwargs):
        super(URL, self).__init__(
            regex='((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xc2\xab\xc2\xbb\xe2\x80\x9c\xe2\x80\x9d\xe2\x80\x98\xe2\x80\x99]))',
            **kwargs)
        
        
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
    EMPTY_LIST = "This field is required"
    
    def __init__(self, field, **kwargs):
        if 'default' not in kwargs:
            kwargs['default'] = []
        super(ListOf, self).__init__(**kwargs)
        self.field = field
        
        
    def validate(self, values):
        if not isinstance(values, list):
            raise ValidationError(self.NOT_A_LIST)
            
        if self.required and len(values) == 0:
            raise ValidationError(self.EMPTY_LIST)
        
        for v in values:
            self.field.validate(v)
        
        return values
        
        
class Anything(Field):
    """
    Passes anything
    """
    
    def _validate(self, value):
        return value
        
        
class Compound(Field):
    """
    Validates a a dict of `key => field`::
    
        v = Entity(foo=Text(), bar=TypeOf(int))
        v.validate({'foo':'oof', 'bar':23}) # ok
        v.validate(5) # nope
        v.validate('foo':'gobot', 'bar':'pizza') # nope
        
        # unspecified keys are filtered
        v.validate({'foo': 'a', 'goo': 'b', 'bar':17})
        # ok -> {'foo': 'a', 'bar':17}
        
        # Fields are optional by default
        v = Entity(foo=Text(), bar=TypeOf(int, default=8))
        v.validate({'foo':'ice cream'}) # -> {'foo':'ice cream', 'bar': 8}
    """
    NOT_A_DICT = "Not a dict"
    
    def __init__(self, required=False, default=None, **kwargs):
        super(Compound, self).__init__(required, default)
        self.fields = kwargs
        self.enforce_required = True
        
        
    def validate(self, value, enforce_required=True):
        self.enforce_required = enforce_required
        return super(Compound, self).validate(value)
        
        
    def _validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError(self.NOT_A_DICT)
        
        validated = {}
        errors = {}
        
        for k,v in self.fields.items():
            unvalidated_value = value.get(k)
            if unvalidated_value is None:
                if v.required and self.enforce_required:
                    errors[k] = 'This field is required.'
                    continue
                elif self.enforce_required:
                    unvalidated_value = v.default
            if unvalidated_value is not None and unvalidated_value != []:
                try:
                    validated[k] = v.validate(unvalidated_value)
                except ValidationError, e:
                    errors[k] = e.message
        
        if errors:
            raise CompoundValidationError(errors)
        
        return validated
    
    
class EntityMixin(object):
    
    def setup(self):
        pass
    
    
class Timestamped(EntityMixin):
    created = DateTime(help="Created")
    modified = DateTime(help="Modified")
    
    def setup(self):
        self.hooks.pre('create', self.on_create)
        self.hooks.pre('update', self.on_modify)
        
        
    def on_create(self, fields):
        now = datetime.utcnow()
        fields['created'] = now
        fields['modified'] = now
        
        
    def on_modify(self, id, fields, replace=False):
        fields['modified'] = datetime.utcnow()
        
        
class Reference(Text):
    
    UNKNOWN = 'No item found with this ID.'
    
    # Reverse delete options
    NULL = 1
    DELETE = 2
    
    def __init__(self, entity, 
            embeddable=False, embed_by_default=True, embedded_fields=None, ondelete=NULL,
            *args, **kwargs):
        self.entity = entity
        self.embeddable = embeddable
        self.embed_by_default = embed_by_default
        self.embedded_fields = embedded_fields
        self.ondelete = ondelete
        self.storage = None
        
        super(Reference, self).__init__(*args, **kwargs)
        
        
    def validate(self, value):
        value = super(Reference, self).validate(value)
        
        if value is None:
            return None
        
        reference = self.storage.get_by_id(self.entity, value, fields={})
        if not reference:
            raise ValidationError(self.UNKNOWN)
        return value
        
        
class Link(object):
    """
    Links define a foreign key relationship. They are read-only.
    """
    
    def __init__(self, entity, field, 
            embeddable=False, embed_by_default=True, embedded_fields=None, 
            multiple=True, hidden=False, help=None):
        self.entity = entity
        self.field = field
        self.embeddable = embeddable
        self.embed_by_default = embed_by_default
        self.embedded_fields = embedded_fields
        self.multiple = multiple
        self.hidden = hidden
        self.storage = None
        self.help = help
    
    
class EntityMeta(type):
    
    def __new__(cls, name, bases, attrs):
        if name == 'Entity':
            return super(EntityMeta, cls).__new__(cls, name, bases, attrs)
        
        hierarchy = []
        all_attrs = {}
        entity_base_found = False
        for b in bases:
            if issubclass(b, Entity):
                if entity_base_found:
                    raise Exception, "Cannot extend more than one Entity"
                entity_base_found = True
                if b != Entity:
                    hierarchy = list(b.hierarchy)
            elif issubclass(b, EntityMixin):
                all_attrs.update(b.__dict__)
        attrs['hierarchy'] = hierarchy
        
        fields = {}
        links = []
        references = []
        hidden_fields = set()
        all_attrs.update(attrs)
        
        for k,v in all_attrs.items():
            if isinstance(v,type) and issubclass(v, Field):
                v = v()
            if isinstance(v, Field):
                if k.startswith('_'):
                    raise Exception, "Fields starting with '_' are reserved."
                fields[k] = v
                if v.hidden:
                    hidden_fields.add(k)
            if isinstance(v, Reference):
                references.append((k,v))
            elif isinstance(v, ListOf) and isinstance(v.field, Reference):
                references.append((k, v.field))
            elif isinstance(v, Link):
                links.append((k,v))
         
        attrs['fields'] = fields
        attrs['references'] = references
        attrs['links'] = links
        attrs['links_and_references'] = links + references
        attrs['hidden_fields'] = hidden_fields
        
        embeddable = set()
        embed_by_default = set()
        
        for k,v in attrs['links_and_references']:
            if v.embeddable:
                embeddable.add(k)
                if v.embed_by_default:
                    embed_by_default.add(k)
        
        attrs['embeddable'] = embeddable
        attrs['embed_by_default'] = embed_by_default
        
        for entity_cls in attrs['hierarchy']:
            attrs['fields'].update(entity_cls.fields)
            attrs['references'] += entity_cls.references
            attrs['links'] += entity_cls.links
            attrs['links_and_references'] += entity_cls.links_and_references
            attrs['hidden_fields'].update(entity_cls.hidden_fields)
            attrs['embeddable'].update(entity_cls.embeddable)
            attrs['embed_by_default'].update(entity_cls.embed_by_default)
        
        attrs['visible_fields'] = set(attrs['fields'].keys()).difference(attrs['hidden_fields'])
        attrs['validator'] = Compound(**fields)
        attrs['children'] = []
        
        new_cls = super(EntityMeta, cls).__new__(cls, name, bases, attrs)
        
        for b in new_cls.hierarchy:
            b.children.append(new_cls)
        
        new_cls.hierarchy.append(new_cls)
        
        return new_cls
        
        
class Entity(object):
    
    __metaclass__ = EntityMeta
    
    versioned = False
    
    def __init__(self):
        self.hooks = EventManager('create', 'update', 'delete')
        for base in self.__class__.__bases__:
            if issubclass(base, EntityMixin):
                base.setup(self)
                
                
    def is_multiple_link(self, link):
        if isinstance(link, ListOf) or isinstance(link, Link) and link.multiple:
            return True
        else:
            return False
    


class Model(object):
    """
    A collection of linked entities.
    """
    
    def __init__(self, storage, entities):
        self.entities = set(entities)
        self.entities_by_name = dict([(e.__name__, e) for e in entities])
        self.storage = storage
        if self.storage is not None:
            self.storage.setup(self)
        self.check_references()
        
        
    def has_entity(self, entity):
        return entity in self.entities
        
        
    def check_references(self):
        # First make sure all references have a reference to their entity class
        for entity in self.entities:
            for reference_name, reference in entity.links_and_references:
                if isinstance(reference.entity, basestring):
                    referenced_entity = self.entities_by_name.get(reference.entity)
                    if not referenced_entity:
                        raise Exception, "Can't resolve reference to entity '%s'" % reference.entity
                    reference.entity = referenced_entity
        
        for entity in self.entities:
            # Disallow references to entities outside the model
            for reference_name, reference in entity.links_and_references:
                if not self.has_entity(reference.entity):
                    raise Exception, "Attempting to reference to an entity '%s' that is outside the model" % reference.entity.__name__
                reference.storage = self.storage
                