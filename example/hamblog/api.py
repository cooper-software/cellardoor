from cellardoor.api import API
from cellardoor.api.methods import LIST, GET, CREATE, UPDATE, DELETE, ALL
from . import model
from .authorization import admin_or_self, admin_or_user


class People(api.Interface):
	entity = model.Person
	plural_name = 'people'
	method_authorization = {
		(LIST, GET, CREATE): None,
		(UPDATE, DELETE): admin_or_self),
	}
	enabled_filters = ('first_name', 'last_name')
	enabled_sort = ('first_name', 'last_name', 'created')
	default_sort = ('+last_name', '+created')
	hidden_field_authorization = admin_or_self
	
	
class Tags(api.Interface):
	entity = model.Tag
	method_authorization = {
		(LIST, GET): None,
		(CREATE, UPDATE, DELETE), admin_or_user)
	}
	enabled_filters = ('name', 'slug')
	enabled_sort = ('name', 'slug')
	default_sort = ('+name',)
	
	
class Posts(api.Interface):
	entity = model.Post
	method_authorization = {
		(LIST, GET): None,
		(CREATE, UPDATE, DELETE), admin_or_user)
	}
	enabled_filters = ('title', 'slug', 'content')
	enabled_sort = ('published', 'created', 'modified', 'slug')
	default_sort = ('-published', '-modified')