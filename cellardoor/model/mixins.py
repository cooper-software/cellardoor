from datetime import datetime
from .fields import DateTime


__all__ = ['Timestamped']


class Timestamped(object):
    
    created = DateTime(help="Created")
    modified = DateTime(help="Modified")
    
    def before_create(self, fields, *args, **kwargs):
        now = datetime.utcnow()
        fields['created'] = now
        fields['modified'] = now
        
        
    def before_update(self, id, fields, *args, **kwargs):
        fields['modified'] = datetime.utcnow()
        