from hammock import create_api
from hammock.views import MinimalView, SirenView
from hammock.auth import TokenAuthenticator
from .resources import PeopleResource, TagsResource, PostsResource
from .auth import token_auth, LoginResource
from .storage import storage


api = create_api(
	resources=(PeopleResource, TagsResource, PostsResource),
	views=(MinimalView, SirenView),
	authenticators=(token_auth,),
	storage=storage
)

api.add_resource('/login', LoginResource())