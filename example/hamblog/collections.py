from hammock.collection import Collection
from hammock.methods import LIST, GET, CREATE, UPDATE, DELETE, ALL
from hammock import auth
from . import model


admin_or_self = (auth.identity.role == 'admin') | (auth.item.id == auth.identity.id)
admin_or_user = (auth.identity.role == 'admin') | (auth.identity.role == 'user')


class PeopleCollection(Collection):
	entity = model.Person
	plural_name = 'people'
	links = {
		'posts': 'PostCollection'
	}
	enabled_methods = ALL
	enabled_filters = ('first_name', 'last_name')
	enabled_sort = ('first_name', 'last_name', 'created')
	default_sort = ('+last_name', '+created')
	method_authorization = (
		((UPDATE, DELETE), admin_or_self),
	)
	hidden_field_authorization = admin_or_self
	
	
	
class TagsCollection(Collection):
	entity = model.Tag
	enabled_methods = ALL
	enabled_filters = ('name', 'slug')
	enabled_sort = ('name', 'slug')
	default_sort = ('+name',)
	method_authorization = (
		((CREATE, UPDATE, DELETE), admin_or_user)
	)
	
	
class PostsCollection(Collection):
	entity = model.Post
	enabled_methods = ALL
	enabled_filters = ('title', 'slug', 'content')
	enabled_sort = ('published', 'created', 'modified', 'slug')
	default_sort = ('-published', '-modified')
	authorization = (
		((CREATE, UPDATE, DELETE), admin_or_user)
	)