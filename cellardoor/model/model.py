import inspect
from  ..events import EventManager
from .fields import Field, ListOf, Compound, Text, ValidationError

__all__ = [
    'Entity',
    'Link',
    'InverseLink',
    'Model',
    'InvalidModelException'
]


class InvalidModelException(Exception):
    pass

        
class Link(Text):
    
    UNKNOWN = 'No item found with this ID.'
    
    # Reverse delete options
    NULLIFY = 1
    CASCADE = 2
    
    def __init__(self, entity, 
            embeddable=False, embed_by_default=True, embedded_fields=None, ondelete=NULLIFY,
            *args, **kwargs):
        self.entity = entity
        self.embeddable = embeddable
        self.embed_by_default = embed_by_default
        self.embedded_fields = embedded_fields
        self.ondelete = ondelete
        self.model = None
        
        super(Link, self).__init__(*args, **kwargs)
        
        
    def validate(self, value):
        value = super(Link, self).validate(value)
        
        if value is None:
            return None
        
        reference = self.model.storage.get_by_id(self.entity, value, fields={})
        if not reference:
            raise ValidationError(self.UNKNOWN)
        return value
        
        
class InverseLink(object):
    
    def __init__(self, entity, field, 
            embeddable=False, embed_by_default=True, embedded_fields=None, 
            multiple=True, hidden=False, label=None, description=None):
        self.entity = entity
        self.field = field
        self.embeddable = embeddable
        self.embed_by_default = embed_by_default
        self.embedded_fields = embedded_fields
        self.multiple = multiple
        self.hidden = hidden
        self.model = None
        self.label = label
        self.description = description
    


class EntityType(type):
    
    def __new__(cls, name, bases, attrs):
        if name == 'Entity':
            return super(EntityType, cls).__new__(cls, name, bases, attrs)
        
        # Get all the mixins from the base classes and make
        # sure we aren't inheriting from more than one entity
        hierarchy = []
        mixins = set(attrs['mixins']) if attrs.get('mixins') else set()
        parent = None
        
        for base in bases:
            if issubclass(base, Entity):
                if parent:
                    raise Exception, "Cannot extend more than one Entity"
                parent = base
                if base.__name__ != 'Entity':
                    hierarchy = list(base.hierarchy)
                    hierarchy.append(base)
                    #if hasattr(base, 'mixins') and base.mixins:
                    #    mixins.update(base.mixins)
        
        
        # Add fields and hooks from the mixins
        hooks = EventManager('create', 'update', 'delete')
        
        if parent and hasattr(parent, 'hooks'):
            hooks.update_from(parent.hooks)
        
        if mixins:
            for mixin in mixins:
                if inspect.isclass(mixin):
                    mixin = mixin()
                for k,v in inspect.getmembers(mixin):
                    if k not in attrs and isinstance(v, (Field, Link, InverseLink)):
                        attrs[k] = v
                    if k.startswith('before_') or k.startswith('after_'):
                        parts = k.split('_')
                        when, event = parts[0], '_'.join(parts[1:])
                        method_name = '%s_%s' % (when, event)
                        getattr(hooks, method_name)(v)
        
        fields = {}
        hidden_fields = set()
        links = {}
        
        # Make sure all fields are instantiated, no fields are using a reserved name
        # and put fields into their categorized buckets for quick lookup later.
        for k,v in attrs.items():
            if isinstance(v, type) and issubclass(v, Field):
                v = v()
            if isinstance(v, Field):
                if k.startswith('_'):
                    raise Exception, "Fields starting with '_' are reserved."
                fields[k] = v
                if v.hidden:
                    hidden_fields.add(k)
            if isinstance(v, (Link, InverseLink)):
                links[k] = v
            elif isinstance(v, ListOf) and isinstance(v.field, (Link, InverseLink)):
                links[k] = v.field
        
        embeddable = set()
        embed_by_default = set()
        
        for k,v in links.items():
            if v.embeddable:
                embeddable.add(k)
                if v.embed_by_default:
                    embed_by_default.add(k)
        
        # Add all the fields from the base entities to the categorized buckets
        for entity_cls in hierarchy:
            fields.update(entity_cls.fields)
            links.update(entity_cls.links)
            hidden_fields.update(entity_cls.hidden_fields)
            embeddable.update(entity_cls.embeddable)
            embed_by_default.update(entity_cls.embed_by_default)
        
        visible_fields = set(fields.keys()).difference(hidden_fields)
        
        # Create the new class
        attrs.update(dict(
            hooks = hooks,
            hierarchy = hierarchy,
            fields = fields,
            hidden_fields = hidden_fields,
            visible_fields = visible_fields,
            links = links,
            embeddable = embeddable,
            embed_by_default = embed_by_default,
            children = [],
            validator = Compound(**fields),
            inverse_links = {}
        ))
        
        new_cls = super(EntityType, cls).__new__(cls, name, bases, attrs)
        
        # Set up the default hooks, if any
        for k,v in attrs.items():
            if k.startswith('before_') or k.startswith('after_'):
                parts = k.split('_')
                when, event = parts[0], '_'.join(parts[1:])
                method_name = '%s_%s' % (when, event)
                getattr(new_cls.hooks, method_name)(v.__get__(new_cls, new_cls.__class__))
        
        # Add the new class to the children list of its base entities
        for base in hierarchy:
            base.children.append(new_cls)
        
        # Register the class with its model
        new_cls.model.add_entity(new_cls)
        
        return new_cls
        
        
    def get_link(cls, name):
        link = cls.links.get(name)
        if not link:
            return None
        if not link.model:
            link.model = cls.model
            if isinstance(link.entity, basestring):
                try:
                    link.entity = cls.model.entities[link.entity]
                except KeyError:
                    raise InvalidModelException, "The model has no entity '%s'" % link.entity
            elif link.entity not in cls.model:
                raise InvalidModelException, "The model has no entity '%s'" % link.entity.__name__
        return link
        
        
    def get_links(cls):
        link_names = cls.links.keys()
        return dict(zip(link_names, map(cls.get_link, link_names)))
        
        
    def is_multiple_link(cls, link):
        return isinstance(link, ListOf) or (isinstance(link, InverseLink) and link.multiple)
        
        
            
class Entity(object):
    
    __metaclass__ = EntityType
    
    mixins = []
    
    

class Model(object):
    """
    A collection of linked entities.
    """
    
    def __init__(self, name=None, storage=None):
        self.name = name
        self.storage = storage
        self.Entity = type('Entity', (Entity,), {'model':self})
        self.entities = {}
        self.is_frozen = False
        
        
    def __repr__(self):
        return 'Model(name=%s, storage=%s)' % (repr(self.name), repr(self.storage))
        
        
    def add_entity(self, entity):
        if self.is_frozen:
            raise Exception, "Attempting to add entity '%s' to a frozen model" % entity.__name__
        if entity.__name__ in self.entities:
            raise Exception, "Attempting to redefine the entity %s" % entity.__name__
        self.entities[entity.__name__] = entity
        
        
    def __contains__(self, entity):
        return entity.__name__ in self.entities
        
        
    def __getattr__(self, name):
        return self.entities[name]
        
        
    def freeze(self):
        if not self.is_frozen:
            self.is_frozen = True
            self.storage.setup(self)
            for entity in self.entities.values():
                for link_name in entity.links:
                    link = entity.get_link(link_name)
                    if not isinstance(link, InverseLink):
                        is_multiple = isinstance(getattr(entity, link_name), ListOf)
                        inverse_link = InverseLink(entity, link_name, multiple=is_multiple)
                        if link.ondelete not in link.entity.inverse_links:
                            link.entity.inverse_links[link.ondelete] = []
                        link.entity.inverse_links[link.ondelete].append(inverse_link)