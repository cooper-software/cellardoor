import inspect
from  ..events import EventManager
from .fields import Field, ListOf, Compound, Text, ValidationError

__all__ = [
    'Entity',
    'Reference',
    'Link',
    'Model'
]
       
        
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
        mixins = set(attrs.get('mixins', []))
        for b in bases:
            if issubclass(b, Entity):
                if entity_base_found:
                    raise Exception, "Cannot extend more than one Entity"
                entity_base_found = True
                if b != Entity:
                    hierarchy = list(b.hierarchy)
                    if hasattr(b, 'mixins'):
                        mixins.update(b.mixins)
        attrs['hierarchy'] = hierarchy
        
        attrs['hooks'] = EventManager('create', 'update', 'delete')
        
        if mixins:
            for m in mixins:
                if inspect.isclass(m):
                    m = m()
                for k,v in inspect.getmembers(m):
                    if k not in attrs and isinstance(v, (Field, Reference, Link)):
                        attrs[k] = v
                    if k.startswith('on_pre_') or k.startswith('on_post_'):
                        parts = k.split('_')
                        when, event = parts[1], '_'.join(parts[2:])
                        getattr(attrs['hooks'], when)(event, v)
        
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
        for k,v in inspect.getmembers(self):
            if k.startswith('on_pre_') or k.startswith('on_post_'):
                parts = k.split('_')
                when, event = parts[1], '_'.join(parts[2:])
                getattr(self.hooks, when)(event, v)
        
    
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
                