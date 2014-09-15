import falcon
from hammock import Hammock
from hammock.falcon import add_to_falcon
from hammock.views import MinimalView, SirenView
from hammock.auth import TokenAuthenticator
from .collections import PeopleCollection, TagsCollection, PostsCollection
from .auth import token_auth, LoginResource
from .storage import storage


hammock_api = Hammock(
		PeopleCollection, TagsCollection, PostsCollection,
		authenticators=(token_auth,),
		storage=storage)

falcon_api = falcon.API()
falcon_api.add_resource('/login', LoginResource())

add_to_falcon(falcon_api, hammock_api)