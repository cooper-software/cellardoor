import falcon
from hammock import Hammock
from hammock.falcon import add_to_falcon
from hammock.views import MinimalView, SirenView
from .collections import PeopleCollection, TagsCollection, PostsCollection
from .auth import LoginResource
from .storage import storage


hammock_api = Hammock(
		PeopleCollection, TagsCollection, PostsCollection,
		storage=storage)

falcon_api = falcon.API()
falcon_api.add_resource('/login', LoginResource())

add_to_falcon(falcon_api, hammock_api)