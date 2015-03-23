import re
from datetime import datetime
from cellardoor.model import *
from .fields import *
from .storage import storage
from .hash_password import hash_password


model = Model(storage)


class Slug(Text):
	
	def __init__(self, *args, **kwargs):
		super(Slug, self).__init__(maxlength=50, regex=re.compile('^[\w\-]+$', re.UNICODE))
		
		
class Password(Text):
    
    def _validate(self, value):
        return hash_password(value)
        
        
class Timestamped(Mixin):
	created = DateTime(default=datetime.utcnow)
	modified = DateTime(default=datetime.utcnow, always_now=True)


class Person(model.Entity):
	mixins = (Timestamped,)
	first_name = Text(maxlength=50, required=True)
	last_name = Text(maxlength=50, required=True)
	email = Email(required=True, hidden=True)
	password = Password(maxlength=50, hidden=True, required=True)
	role = Enum('anonymous', 'normal', 'admin', default='anonymous')
	
	
class Post(model.Entity):
	mixins = (Timestamped,)
	status = Enum('draft', 'published', default='draft')
	publish_date = DateTime()
	slug = Slug(required=True),
	author = Reference(Person, required=True, storage=storage)
	title = Text(maxlength=200, required=True)
	content = Text(maxlength=10000)
	tags = ListOf(Reference('Tag', storage=storage))
	
	
class Tag(model.Entity):
	mixins = (Timestamped,)
	name = Text(maxlength=50, required=True)
	slug = Slug(required=True)
	
