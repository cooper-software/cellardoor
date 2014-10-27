import re
from datetime import datetime
from cellardoor.model import *
from .storage import storage
from .hash_password import hash_password


model = Model(storage)


class Slug(Text):
	
	def __init__(self, *args, **kwargs):
		super(Slug, self).__init__(maxlength=50, regex=re.compile('^[\w\-]+$', re.UNICODE))


class Person(model.Entity):
	mixins = (Timestamped,)
	first_name = Text(maxlength=50, required=True)
	last_name = Text(maxlength=50, required=True)
	email = Email(required=True, hidden=True)
	password = Text(maxlength=50, hidden=True, required=True)
	role = Enum('anonymous', 'normal', 'admin', default='anonymous')
	
	
	def before_create(self, fields, context):
		self.hash_password(fields)
		
	def before_update(self, id, fields, context):
		self.hash_password(fields)
		
	def hash_password(self, fields):
		if 'password' in fields:
			fields['password'] = hash_password(fields['password'])
	
	
class Post(model.Entity):
	versioned = True
	mixins = (Timestamped,)
	status = Enum('draft', 'published', default='draft')
	publish_date = DateTime()
	slug = Slug(required=True),
	author = Reference(Person, required=True, storage=storage)
	title = Text(maxlength=200, required=True)
	content = Text(maxlength=10000)
	tags = ListOf(Reference('Tag', storage=storage))
	
	
class Tag(model.Entity):
	name = Text(maxlength=50, required=True)
	slug = Slug(required=True)
	
