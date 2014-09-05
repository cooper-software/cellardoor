from hammock.resource import Resource
from hammock.methods import LIST, GET, CREATE, UPDATE, DELETE, ALL
from hammock import auth
from . import model


class PeopleResource(Resource):
	plural_name = 'people'
	
	model = model.Person
	link_resources = {
		'posts': 'PostResource'
	}
	
	enabled_methods = ALL
	enabled_filters = ('first_name', 'last_name')
	enabled_sort = ('first_name', 'last_name', 'created')
	default_sort = ('+last_name', '+created')
	
	authorization = (
		((UPDATE, DELETE), auth.role_matches('admin') or auth.id_matches('id')),
	)
	
	show_hidden = auth.role_matches('admin') or auth.field_matches('id')
	
	
	
class TagsResource(Resource):
	model = model.Tag
	
	enabled_methods = ALL
	enabled_filters = ('name', 'slug')
	enabled_sort = ('name', 'slug')
	default_sort = ('+name',)
	
	authorization = (
		((CREATE, UPDATE, DELETE), auth.role_matches('admin', 'user'))
	)
	
	
	
class PostsResource(Resource):
	model = model.Post
	
	enabled_methods = ALL
	enabled_filters = ('title', 'slug', 'content')
	enabled_sort = ('published', 'created', 'modified', 'slug')
	default_sort = ('-published', '-modified')
	
	authorization = (
		((CREATE, UPDATE, DELETE), auth.role_matches('admin', 'user'))
	)