import unittest
from copy import deepcopy
from mock import Mock
import random
from cellardoor.model import Model, Entity, Link, InverseLink, Text, ListOf, Integer, Float, Enum
from cellardoor.api import API
from cellardoor.api.methods import ALL, LIST, GET, CREATE
from cellardoor.storage import Storage
from cellardoor import errors
from cellardoor.authorization import ObjectProxy

identity = ObjectProxy('identity')
item = ObjectProxy('item')

class CopyingMock(Mock):
	
	def __call__(self, *args, **kwargs):
		args = deepcopy(args)
		kwargs = deepcopy(kwargs)
		return super(CopyingMock, self).__call__(*args, **kwargs)

storage = Storage()
model = Model(storage=storage)
api = API(model)


class Foo(model.Entity):
	stuff = Text(required=True)
	optional_stuff = Text()
	bars = InverseLink('Bar', 'foo')
	bazes = ListOf(Link('Baz'))
	embedded_bazes = ListOf(Link('Baz', embeddable=True))
	embedded_foos = ListOf(Link('Foo', embeddable=True, embed_by_default=False, embedded_fields=('stuff',)))
	secret = Text(hidden=True)
	
	
class Bar(model.Entity):
	foo = Link(Foo)
	embedded_foo = Link(Foo, embeddable=True)
	bazes = ListOf(Link('Baz', ondelete=Link.CASCADE))
	number = Integer()
	name = Text()
	
	
class Baz(model.Entity):
	name = Text(required=True)
	foo = InverseLink(Foo, 'bazes', multiple=False)
	embedded_foo = InverseLink(Foo, 'bazes', multiple=False, embeddable=True, embed_by_default=False)
	
	
class Hidden(model.Entity):
	name = Text(hidden=True)
	foo = Integer
	
	
class Littorina(model.Entity):
	size = Float()
	
	
class Shell(model.Entity):
	color = Enum('Brown', 'Gray', 'Really brown')
	
	
class LittorinaLittorea(Littorina):
	shell = Link('Shell', embeddable=True)
	
	
class Planet(model.Entity):
	pass


class NullSingleTarget(model.Entity):
	pass
	
	
class NullSingleReferrer(model.Entity):
	target = Link(NullSingleTarget)


class NullMultiTarget(model.Entity):
	pass
	
	
class NullMultiReferrer(model.Entity):
	targets = ListOf(Link(NullMultiTarget))
	
	
class CascadeTarget(model.Entity):
	pass
	
	
class CascadeReferrer(model.Entity):
	target = Link(CascadeTarget, ondelete=Link.CASCADE)
	
	
class AnyFunctionAuthModel(model.Entity):
	pass
	
	
class Foos(api.Interface):
	entity = Foo
	method_authorization = {
		ALL: None
	}
	enabled_filters = ('stuff',)
	enabled_sort = ('stuff',)
	hidden_field_authorization = identity.role == 'admin'
	
	
class ReadOnlyFoos(api.Interface):
	entity = Foo
	singular_name = 'readonly_foo'
	method_authorization = {
		(LIST, GET): None
	}
	
	
class Bars(api.Interface):
	entity = Bar
	method_authorization = {
		ALL: None
	}
	enabled_filters = ('number',)
	enabled_sort = ('number', 'name')
	default_sort = ('+name',)
	
	
class Bazes(api.Interface):
	entity = Baz
	plural_name = 'bazes'
	method_authorization = {
		ALL: None
	}
	enabled_filters = ('name',)
	enabled_sort = ('name',)
	default_limit = 10
	max_limit = 20

	
class Hiddens(api.Interface):
	entity = Hidden
	enabled_filters = ('name',)
	enabled_sort = ('name',)
	method_authorization = {
		LIST: identity.exists(),
		CREATE: identity.role == 'admin',
		GET: item.foo == 23
	}
	hidden_field_authorization = identity.foo == 'bar'
	
	
class Littorinas(api.Interface):
	entity = Littorina
	method_authorization = {
		ALL: None
	}
	
	
class Shells(api.Interface):
	entity = Shell
	method_authorization = {
		ALL: None
	}


class Planets(api.Interface):
	entity = Planet
	method_authorization = {
		LIST: item.foo == 23
	}
	
	
class NullSingleTargets(api.Interface):
	entity = NullSingleTarget
	method_authorization = {
		ALL: None
	}
	
	
class NullSingleReferrers(api.Interface):
	entity = NullSingleReferrer
	method_authorization = {
		ALL: None
	}
	
	
class NullMultiTargets(api.Interface):
	entity = NullMultiTarget
	method_authorization = {
		ALL: None
	}
	
	
class NullMultiReferrers(api.Interface):
	entity = NullMultiReferrer
	method_authorization = {
		ALL: None
	}
	
	
class CascadeTargets(api.Interface):
	entity = CascadeTarget
	method_authorization = {
		ALL: None
	}
	
	
class CascadeReferrers(api.Interface):
	entity = CascadeReferrer
	method_authorization = {
		ALL: None
	}
	

auth_fn_get = Mock(return_value=False)
auth_fn_list = Mock(return_value=True)
class AnyFunctionAuthModels(api.Interface):
	entity = AnyFunctionAuthModel
	method_authorization = {
		GET: auth_fn_get,
		LIST: auth_fn_list
	}
	

class InterfaceTest(unittest.TestCase):
	
	def setUp(self):
		storage = Storage()
		model.storage = storage
		for interface in api.interfaces.values():
			interface.set_storage(storage)
			
			
	def get_interface(self, name, storage=None):
		if storage is None:
			storage = Storage()
		interface = api.interfaces[name]
		interface.set_storage(storage)
		return interface
		
		
	def test_create_fail_validation(self):
		"""
		Fails if the request fields don't pass validation.
		"""
		with self.assertRaises(errors.CompoundValidationError):
			api.interfaces['foos'].create({})
	
	
	def test_create_succeed(self):
		"""
		Creates a new item in persistent storage if we pass validation.
		"""
		foos = self.get_interface('foos')
		foos.storage.create = CopyingMock(return_value='123')
		foo = foos.create({'stuff':'foo'})
		foos.storage.create.assert_called_once_with(Foo, {'stuff':'foo'})
		self.assertEquals(foo, {'_id':'123', 'stuff':'foo'})
		
		
	def test_list(self):
		"""
		Returns a list of created items
		"""
		saved_foos = []
		
		for i in range(0,3):
			saved_foos.append(
				{'stuff':'foo#%d' % i, '_id':i}
			)
		
		foos = self.get_interface('foos')
		foos.storage.get = CopyingMock(return_value=saved_foos)
		
		fetched_foos = foos.list()
		foos.storage.get.assert_called_once_with(Foo, sort=(), filter=None, limit=0, offset=0, count=False)
		self.assertEquals(fetched_foos, saved_foos)
		
		
	def test_get(self):
		"""
		Can get a single item
		"""
		foos = self.get_interface('foos')
		foo = {'_id':123, 'stuff':'foo'}
		foos.storage.get_by_id = CopyingMock(return_value=foo)
		fetched_foo = foos.get(foo['_id'])
		foos.storage.get_by_id.assert_called_once_with(Foo, foo['_id'])
		self.assertEquals(fetched_foo, foo)
		
		
	def test_get_nonexistent(self):
		"""
		Trying to fetch a nonexistent item raises an error.
		"""
		foos = self.get_interface('foos')
		foos.storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			foos.get(123)
		
		
	def test_update(self):
		"""
		Can update a subset of fields
		"""
		foos = self.get_interface('foos')
		foo = {'_id':123, 'stuff':'baz'}
		foos.storage.update = Mock(return_value=foo)
		foos.storage.get_by_id = Mock(return_value=foo)
		updated_foo = foos.update(123, {'stuff':'baz'})
		foos.storage.update.assert_called_once_with(Foo, 123, {'stuff':'baz'}, replace=False)
		self.assertEquals(updated_foo, foo)
		
		
	def test_update_nonexistent(self):
		"""
		Trying to update a nonexistent item raises an error.
		"""
		foos = self.get_interface('foos')
		foos.storage.update = Mock(return_value=None)
		foos.storage.get_by_id = Mock(return_value={})
		with self.assertRaises(errors.NotFoundError):
			foos.update(123, {})
		
		
	def test_replace(self):
		"""
		Can replace a whole existing item
		"""
		foos = self.get_interface('foos')
		foo = {'_id':123, 'stuff':'baz'}
		foos.storage.update = Mock(return_value=foo)
		foos.storage.get_by_id = Mock(return_value={})
		updated_foo = foos.replace(123, {'stuff':'baz'})
		foos.storage.update.assert_called_once_with(Foo, 123, {'stuff':'baz'}, replace=True)
		self.assertEquals(updated_foo, foo)
		
		
	def test_replace_nonexistent(self):
		"""
		Trying to replace a nonexistent item raises an error.
		"""
		foos = self.get_interface('foos')
		foos.storage.update = Mock(return_value=None)
		foos.storage.get_by_id = Mock(return_value={})
		with self.assertRaises(errors.NotFoundError):
			foos.replace(123, {'stuff':'foo'})
		
		
	def test_delete_nonexistent(self):
		"""
		Raise an error when trying to delete an item that doesn't exist
		"""
		foos = self.get_interface('foos')
		foos.storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.NotFoundError):
			foos.delete(123, inverse_delete=False)
		
		
	def test_delete(self):
		"""
		Can remove an existing item
		"""
		foos = self.get_interface('foos')
		foos.storage.get_by_id = Mock(return_value={'_id':123, 'stuff':'foo'})
		foos.storage.delete = Mock(return_value=None)
		foos.delete(123, inverse_delete=False)
		foos.storage.get_by_id.assert_called_once_with(Foo, 123)
		foos.storage.delete.assert_called_once_with(Foo, 123)
		
		
	def test_single_link_validation_fail(self):
		"""
		Fails validation if setting a link to a non-existent ID.
		"""
		foos = api.interfaces['foos']
		bars = api.interfaces['bars']
		foos.storage.get_by_id = Mock(return_value=None)
		with self.assertRaises(errors.CompoundValidationError):
			bars.create({'foo':'123'})
		
		
	def test_single_link(self):
		"""
		Can get a link through a link.
		"""
		foo = {'_id':'123', 'stuff':'foo'}
		bar = {'_id':'321', 'foo':'123'}
		
		foos = self.get_interface('foos')
		bars = self.get_interface('bars')
		foos.storage.get_by_id = Mock(return_value=foo)
		bars.storage.get_by_id = Mock(return_value=bar)
		
		linked_foo = bars.link('321', 'foo')
		self.assertEquals(linked_foo, foo)
		bars.storage.get_by_id.assert_called_once_with(Bar, '321')
		foos.storage.get_by_id.assert_called_once_with(Foo, '123')
		
		
	def test_single_link_get_embedded(self):
		"""
		Embedded links are included when fetching the referencing item.
		"""
		
		foo = {'_id':'123', 'stuff':'foo'}
		bar = {'_id':'321', 'embedded_foo':'123'}
		
		foos = self.get_interface('foos')
		bars = self.get_interface('bars')
		foos.storage.get_by_id = Mock(return_value=foo)
		bars.storage.get_by_id = Mock(return_value=bar)
		
		bar = bars.get('321')
		self.assertEquals(bar['embedded_foo'], foo)
		
		
	def test_multiple_link(self):
		"""
		Can set a list of links when creating an item
		"""
		created_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			created_bazes.append(baz)
			baz_ids.append(baz['_id'])
			
		foo = {'_id':'123', 'bazes':baz_ids}
		
		foos = self.get_interface('foos')
		bazes = self.get_interface('bazes')
		foos.storage.get_by_id = Mock(return_value=foo)
		foos.storage.check_filter = Mock(return_value=None)
		bazes.storage.get_by_ids = Mock(return_value=created_bazes)
		bazes.storage.check_filter = Mock(return_value=None)
		
		linked_bazes = foos.link(foo['_id'], 'bazes', sort=('+name',), filter={'name':'foo'}, offset=10, limit=20)
		self.assertEquals(linked_bazes, created_bazes)
		bazes.storage.get_by_ids.assert_called_once_with(Baz, baz_ids, sort=('+name',), filter={'name':'foo'}, offset=10, limit=20, count=False)
		
		
	def test_multiple_link_default_order(self):
		"""
		Linked items are always in field order unless a sort option is set
		"""
		ordered_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			ordered_bazes.append(baz)
			baz_ids.append(baz['_id'])
		
		random_bazes = [b for b in ordered_bazes]
		random.shuffle(random_bazes)
		
		foo = {'_id':'123', 'bazes':baz_ids}
		
		foos = api.interfaces['foos']
		bazes = api.interfaces['bazes']
		foos.storage.get_by_id = Mock(return_value=foo)
		bazes.storage.check_filter = Mock(return_value=None)
		bazes.storage.get_by_ids = Mock(return_value=random_bazes)
		
		linked_bazes = foos.link(foo['_id'], 'bazes')
		self.assertEquals(linked_bazes, ordered_bazes)
		linked_bazes = foos.link(foo['_id'], 'bazes', sort=('+name',))
		self.assertEquals(linked_bazes, random_bazes)
		
		
	def test_multiple_link_get_embedded(self):
		"""
		Embedded link list is included when fetching the referencing item.
		"""
		created_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			created_bazes.append(baz)
			baz_ids.append(baz['_id'])
			
		foo = {'_id':'123', 'embedded_bazes':baz_ids}
		
		foos = self.get_interface('foos')
		bazes = self.get_interface('bazes')
		foos.storage.get_by_id = Mock(return_value=foo)
		bazes.storage.get_by_ids = Mock(return_value=created_bazes)
		
		fetched_foo = foos.get(foo['_id'])
		self.assertEquals(fetched_foo['embedded_bazes'], created_bazes)
		
		
	def test_single_inverse_link(self):
		"""
		Can resolve a single link.
		"""
		created_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			created_bazes.append(baz)
			baz_ids.append(baz['_id'])
			
		foo = {'_id':'123', 'bazes':baz_ids}
		
		foos = self.get_interface('foos')
		bazes = self.get_interface('bazes')
		foos.storage.get = Mock(return_value=[foo])
		bazes.storage.get_by_id = Mock(return_value=created_bazes[0])
		
		linked_foo = bazes.link(baz_ids[0], 'foo')
		bazes.storage.get_by_id.assert_called_once_with(Baz, baz_ids[0])
		foos.storage.get.assert_called_once_with(Foo, filter={'bazes':baz_ids[0]}, limit=1)
		self.assertEquals(linked_foo, foo)
		
		
	def test_single_inverse_link_embedded(self):
		"""
		Single embedded links are automatically resolved.
		"""
		created_bazes = []
		baz_ids = []
		for i in range(0,3):
			baz = { 'name':'Baz#%d' % i, '_id':'%d' % i }
			created_bazes.append(baz)
			baz_ids.append(baz['_id'])
			
		foo = {'_id':'123', 'bazes':baz_ids}
		
		foos = self.get_interface('foos')
		foos.storage.get = Mock(return_value=[foo])
		bazes = self.get_interface('bazes')
		bazes.storage.get_by_id = Mock(return_value=created_bazes[0])
		
		baz = bazes.get(baz_ids[0], embed=('embedded_foo',))
		self.assertEquals(baz['embedded_foo'], foo)
		
		
	def test_multiple_inverse_link(self):
		"""
		Can resolve a multiple link the same way as a link.
		"""
		foo = {'stuff':'foo', '_id':'123'}
		
		bar_items = []
		bar_ids = []
		for i in range(0,3):
			bar = {'foo':foo['_id'], '_id':'%s' % i}
			bar_items.append(bar)
			bar_ids.append(bar['_id'])
		
		foos = self.get_interface('foos')
		foos.storage.get_by_id = Mock(return_value=foo)
		foos.storage.check_filter = Mock(return_value=None)
		bars = self.get_interface('bars')
		bars.storage.get = Mock(return_value=bar_items)
		bars.storage.check_filter = Mock(return_value=None)
		
		linked_bars = api.interfaces['foos'].link(foo['_id'], 'bars', sort=('-name',), filter={'number':'7'}, limit=10, offset=20)
		foos.storage.get_by_id.assert_called_once_with(Foo, foo['_id'])
		bars.storage.get.assert_called_once_with(Bar, sort=('-name',), filter={'foo': '123', 'number':'7'}, limit=10, offset=20, count=False)
		self.assertEquals(linked_bars, bar_items)
		
		
	def test_embed_polymorphic(self):
		"""Interfaces properly embed links when fetching descendants of the interface's entity"""
		littorinas = self.get_interface('littorinas')
		shells = self.get_interface('shells')
		
		littorinas.storage.get = Mock(return_value=[
			{'_id': '1', '_type':'Littorina.LittorinaLittorea', 'shell':'2'}])
		shells.storage.get_by_id = Mock(return_value={'_id':'2', 'color': 'Really brown'})
		
		result = littorinas.list()
		shells.storage.get_by_id.assert_called_once_with(Shell, '2')
		self.assertEquals(result, [{'_id': '1', '_type':'Littorina.LittorinaLittorea', 'shell':{'_id':'2', 'color': 'Really brown'}}])
		
		
	def test_sort_fail(self):
		"""
		Trying to sort by a sort-disabled field raises an error.
		"""
		with self.assertRaises(errors.DisabledFieldError) as cm:
			api.interfaces['foos'].list(sort=('+optional_stuff',))
		
		
	def test_sort_default(self):
		"""
		If no sort is set, the default is used.
		"""
		bars = self.get_interface('bars')
		bars.storage.get = Mock(return_value=[])
		bars.list()
		bars.storage.get.assert_called_once_with(Bar, sort=('+name',), filter=None, limit=0, offset=0, count=False)
		
		
	def test_auth_required_not_present(self):
		"""Raise NotAuthenticatedError if authorization requires authentication and it is not present."""
		with self.assertRaises(errors.NotAuthenticatedError):
			api.interfaces['hiddens'].list()
			
			
	def test_auth_required_present(self):
		"""Don't raise NotAuthenticatedError if authentication is required and present."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.get = Mock(return_value=[])
		hiddens.list(context={'identity':{'foo':'bar'}})
		
		
	def test_auth_failed(self):
		"""Raises NotAuthorizedError if the authorization rule fails"""
		with self.assertRaises(errors.NotAuthorizedError):
			api.interfaces['hiddens'].create({}, context={'identity':{}})
			
		with self.assertRaises(errors.NotAuthorizedError):
			api.interfaces['hiddens'].create({}, context={'identity':{'role':'foo'}})
			
			
	def test_auth_pass(self):
		"""Does not raise NotAuthorizedError if the authorization rule passes"""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.create = Mock(return_value={})
		hiddens.create({}, context={'identity':{'role':'admin'}})
		
		
	def test_auth_result_fail(self):
		"""Raises NotAuthorizedError if a result rule doesn't pass."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.get_by_id = Mock(return_value={'foo':700})
		with self.assertRaises(errors.NotAuthorizedError):
			hiddens.get(123)
			
			
	def test_auth_result_fail_list(self):
		"""Raises NotAuthorizedError if a member of a result list doesn't pass a rule."""
		planets = self.get_interface('planets')
		planets.storage.get = Mock(return_value=[{'foo':700}])
		with self.assertRaises(errors.NotAuthorizedError):
			planets.list()
		
		
	def test_auth_result_pass(self):
		"""Does not raise NotAuthorizedError if a result rule passes."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.get_by_id = Mock(return_value={'foo':23})
		hiddens.get(123)
		
		
	def test_auth_arbitrary_function(self):
		"""Will use an arbitrary function to check authorization"""
		anyfunctionauthmodels = self.get_interface('anyfunctionauthmodels')
		anyfunctionauthmodels.storage.get_by_id = Mock(return_value={'foo':'123'})
		anyfunctionauthmodels.storage.get = Mock(return_value=[{'foo':'a'}])
		
		with self.assertRaises(errors.NotAuthorizedError):
			anyfunctionauthmodels.get('666')
		
		auth_fn_get.assert_called_once_with({'item':{'foo':'123'}})
		
		anyfunctionauthmodels.list()
		auth_fn_list.assert_called_once_with({'item':{'foo':'a'}})
		
		
	def test_hidden_result(self):
		"""Hidden fields aren't shown in results."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.create = Mock(return_value={'_id':'123', 'name':'foo'})
		obj = hiddens.create({'name':'foo'}, context={'identity':{'role':'admin'}})
		self.assertNotIn('name', obj)
		
		
	def test_hidden_show_fail(self):
		"""Hidden fields aren't shown in results even when show_hidden=True if the user is not authorized."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.get_by_id = Mock(return_value={'_id':'123', 'name':'foo', 'foo':23})
		obj = hiddens.get('123', show_hidden=True)
		self.assertNotIn('name', obj)
		
		
	def test_hidden_succeed(self):
		"""Hidden fields are shown when show_hidden=True and the user is authorized."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.get_by_id = Mock(return_value={'_id':'123', 'name':'foo', 'foo':23})
		obj = hiddens.get('123', show_hidden=True, context={'identity':{'foo':'bar'}})
		self.assertIn('name', obj)
		
		
	def test_hidden_filter(self):
		"""Can't filter by a hidden field without authorization."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.check_filter = Mock(side_effect=errors.DisabledFieldError)
		with self.assertRaises(errors.DisabledFieldError):
			hiddens.list(filter={'name':'zoomy'}, context={'identity':{}})
		hiddens.storage.check_filter.assert_called_once_with({'name':'zoomy'}, set(['_type', '_id']), {'identity': {}})
		
		
	def test_hidden_filter_authorized(self):
		"""Can filter by a hidden field when authorized."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.check_filter = Mock(return_value=None)
		hiddens.storage.get = Mock(return_value=[])
		hiddens.list(filter={'name':'zoomy'}, context={'identity':{'foo':'bar'}})
		hiddens.storage.check_filter.assert_called_once_with({'name':'zoomy'}, set(['name', '_type', '_id']),  {'item': [], 'identity': {'foo': 'bar'}})
		
		
	def test_hidden_sort_fail(self):
		"""Can't sort by a hidden field without authorization."""
		with self.assertRaises(errors.DisabledFieldError) as cm:
			api.interfaces['hiddens'].list(sort=('+name',), context={'identity':{}})
		self.assertEquals(cm.exception.message, 'The "name" field cannot be used for sorting.')
		
		
	def test_authorization_bypass(self):
		"""Can bypass authorization for methods, filters and sort."""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.get = Mock(return_value=[{'name':'zoomy', 'foo':23}])
		results = hiddens.list(filter={'name':'zoomy'}, sort=('+name',), bypass_authorization=True, show_hidden=True)
		hiddens.storage.get.assert_called_once_with(Hidden, sort=('+name',), filter={'name':'zoomy'}, limit=0, offset=0, count=False)
		self.assertEquals(results, [{'name':'zoomy', 'foo':23}])
		
		
	def test_hooks(self):
		foos = self.get_interface('foos')
		foos.storage.get_by_id = Mock(return_value={'foo':23})
		foos.storage.get = Mock(return_value=[{'foo':23}])
		foos.storage.create = Mock(return_value=123)
		foos.storage.update = Mock(return_value={'foo':23})
		foos.storage.delete = Mock()
		foos.inverse_delete = Mock()
		foos.storage.check_filter = Mock()
		foos.before_get = Mock()
		foos.after_get = Mock()
		foos.before_list = Mock()
		foos.after_list = Mock()
		foos.before_create = Mock()
		foos.after_create = Mock()
		foos.before_update = Mock()
		foos.after_update = Mock()
		foos.before_delete = Mock()
		foos.after_delete = Mock()
		context = {'identity':{'foo':'bar'}}
		
		foos.get(123, context=context)
		foos.before_get.assert_called_once_with(context['identity'], 123)
		foos.after_get.assert_called_once_with(context['identity'], {'foo':23})
		
		foos.list(filter={'stuff':'things'}, context=context)
		foos.before_list.assert_called_once_with(context['identity'], {'stuff':'things'})
		foos.after_list.assert_called_once_with(context['identity'], [{'foo':23}])
		
		foos.create({'stuff':'things'}, context=context)
		foos.before_create.assert_called_once_with(context['identity'], {'stuff':'things'})
		foos.after_create.assert_called_once_with(context['identity'], {'stuff':'things', '_id':123})
		
		foos.update(123, {'things':'stuff'}, context=context)
		foos.before_update.assert_called_once_with(context['identity'], {'foo':23}, {'things':'stuff'})
		foos.after_update.assert_called_once_with(context['identity'], {'foo':23})
		
		foos.delete(123, context=context)
		foos.before_delete.assert_called_once_with(context['identity'], {'foo':23})
		foos.after_delete.assert_called_once_with(context['identity'], {'foo':23})
		
		
	def test_disabled_method(self):
		"""An error is raised when attempting to call a disabled method."""
		with self.assertRaises(errors.DisabledMethodError):
			api.interfaces['readonly_foos'].create({})
		
		
	def test_default_limit(self):
		"""A default limit is used when limit is not passed"""
		bazes = self.get_interface('bazes')
		bazes.storage.get = Mock(return_value=[])
		bazes.list()
		bazes.storage.get.assert_called_once_with(Baz, sort=(), filter=None, offset=0, limit=10, count=False)
		
		
	def test_max_limit(self):
		"""Limit can't exceed max_limit"""
		bazes = self.get_interface('bazes')
		bazes.storage.get = Mock(return_value=[])
		bazes.list(limit=50)
		bazes.storage.get.assert_called_once_with(Baz, sort=(), filter=None, offset=0, limit=20, count=False)
		
		
	def test_default_embedded_not_default(self):
		"""A link can be embeddable but not embedded"""
		foos = self.get_interface('foos')
		foos.storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		foos.storage.get_by_ids = Mock(return_value=[])
		foos.list()
		self.assertFalse(foos.storage.get_by_ids.called)
		
		
	def test_default_not_embedded_not_default_included(self):
		"""A link that is not embedded by default can still be embedded"""
		foos = self.get_interface('foos')
		foos.storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		foos.storage.get_by_ids = Mock(return_value=[])
		foos.list(embed=['embedded_foos'])
		foos.storage.get_by_ids.assert_called_once_with(Foo, ['1','2','3'], sort=(), filter=None, limit=0, offset=0, count=False)
		
		
	def test_embeddable_included_if_fields_set(self):
		"""An embeddable field is included if it is in the fields argument"""
		foos = self.get_interface('foos')
		foos.storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		foos.storage.get_by_ids = Mock(return_value=[])
		foos.list(fields=['embedded_foos'])
		foos.storage.get_by_ids.assert_called_once_with(Foo, ['1','2','3'], sort=(), filter=None, limit=0, offset=0, count=False)
		
		
	def test_embeddable_fields(self):
		"""Only fields in an entity's embedded_fields list are included"""
		foos = self.get_interface('foos')
		foos.storage.get = Mock(return_value=[{'_id':'123', 'embedded_foos':['1','2','3']}])
		foos.storage.get_by_ids = Mock(return_value=[{'_id':'2', 'stuff':123, 'optional_stuff':456}])
		result = foos.list(embed=('embedded_foos',))
		self.assertEquals(result, [{'_id':'123', 'embedded_foos':[{'_id':'2', 'stuff':123}]}])
		
		
	def test_field_subset(self):
		"""Can fetch only a subset of fields"""
		foos = self.get_interface('foos')
		foos.storage.get_by_id = CopyingMock(return_value={'_id':'123', 'stuff':123, 'optional_stuff':456})
		result = foos.get('123', fields=('optional_stuff',))
		self.assertEquals(result, {'_id':'123', 'optional_stuff':456})
		
		
	def test_no_fields(self):
		"""Only an item's ID is included if fields is an empty list"""
		foos = self.get_interface('foos')
		foos.storage.get_by_id = CopyingMock(return_value={'_id':'123', 'stuff':123, 'optional_stuff':456})
		result = foos.get('123', fields=())
		self.assertEquals(result, {'_id':'123'})
		
		
	def test_fields_empty(self):
		"""All of an item's visible fields are returned if the fields list is omitted"""
		foo = {'_id':'123', 'stuff':123, 'optional_stuff':456}
		foos = self.get_interface('foos')
		foos.storage.get_by_id = CopyingMock(return_value=foo)
		result = foos.get('123')
		self.assertEquals(result, foo)
		
		
	def test_fields_empty_hidden_field(self):
		"""All of an item's visible fields are returned if the fields list is omitted when an entity has hidden fields"""
		hiddens = self.get_interface('hiddens')
		hiddens.storage.get_by_id = CopyingMock(return_value={'_id':'123', 'name':'hidden', 'foo':23})
		result = hiddens.get('123')
		self.assertEquals(result, {'_id':'123', 'foo':23})
		
		
	def test_fields_empty_hidden_list(self):
		"""All of an item's visible fields are returned when listing items"""
		foos = self.get_interface('foos')
		foos.storage.get = CopyingMock(return_value=[{'_id':'123', 'stuff':'foo', 'secret':'i like valuer'}])
		result = foos.list()
		self.assertEquals(result, [{'_id':'123', 'stuff':'foo'}])
		
		
	def test_count(self):
		"""Can get a count instead of a list of items"""
		foos = self.get_interface('foos')
		foos.storage.get = Mock(return_value=42)
		result = foos.list(count=True)
		self.assertEquals(result, 42)
		foos.storage.get.assert_called_once_with(Foo, filter=None, sort=(), offset=0, limit=0, count=True)
		
		
	def test_count_link(self):
		"""Can count a list link instead of getting the items"""
		foos = self.get_interface('foos')
		bazes = self.get_interface('bazes')
		foos.storage.get_by_id = Mock(return_value={'_id':'123', 'bazes':['1','2','3']})
		bazes.storage.get_by_ids = Mock(return_value=42)
		result = foos.link('123', 'bazes', count=True)
		self.assertEquals(result, 42)
		bazes.storage.get_by_ids.assert_called_with(Baz, ['1','2','3'], filter=None, sort=(), offset=0, limit=10, count=True)
		
		
	def test_count_inverse_link(self):
		"""Can count a multiple link instead of getting the items"""
		foo = {'stuff':'foo', '_id':'123'}
		
		bars = []
		for i in range(0,3):
			bar = {'foo':foo['_id'], '_id':'%s' % i}
			bars.append(bar)
		
		foos = api.interfaces['foos']
		bars = api.interfaces['bars']
		foos.storage.get_by_id = Mock(return_value=foo)
		bars.storage.get = Mock(return_value=3)
		bars.storage.check_filter = Mock(return_value=None)
		
		result = foos.link(foo['_id'], 'bars', count=True)
		self.assertEquals(result, 3)
		bars.storage.get.assert_called_once_with(Bar, filter={'foo':'123'}, sort=('+name',), offset=0, limit=0, count=True)
		
		
	def test_reverse_delete_null_single(self):
		"""Removing a single linked item with a NULL rule, nulls the referencing item's link field"""
		targets = self.get_interface('nullsingletargets')
		targets.storage.get_by_id = Mock(return_value={'_id':'123'})
		targets.storage.delete = Mock()
		
		referrers = self.get_interface('nullsinglereferrers')
		referrers.storage.get = Mock(return_value=[{'_id':'666'}])
		referrers.storage.check_filter = Mock(return_value=None)
		referrers.storage.update = Mock(return_value={})
		referrers.storage.get_by_id = Mock(return_value={})
		
		targets.delete('123')
		
		targets.storage.get_by_id.assert_called_once_with(NullSingleTarget, '123')
		targets.storage.delete.assert_called_once_with(NullSingleTarget, '123')
		referrers.storage.get.assert_called_once_with(NullSingleReferrer, filter={'target':'123'}, count=False, sort=(), offset=0, limit=0)
		referrers.storage.update.assert_called_once_with(NullSingleReferrer, '666', {'target':None}, replace=False)
		
		
	def test_reverse_delete_null_multi(self):
		"""Removing a multi-linked item with a NULL rule, removes the links in the referencing item's field"""
		targets = api.interfaces['nullmultitargets']
		targets.storage.get_by_id = Mock(return_value={'_id':'123'})
		targets.storage.delete = Mock()
		
		referrers = api.interfaces['nullmultireferrers']
		referrers.storage.get = Mock(return_value=[{'_id':'666', 'targets':['555', '123', '888']}])
		referrers.storage.check_filter = Mock(return_value=None)
		referrers.storage.update = Mock(return_value={})
		
		targets.delete('123')
		
		targets.storage.get_by_id.assert_any_call(NullMultiTarget, '123')
		targets.storage.get_by_id.assert_any_call(NullMultiTarget, '555', fields={})
		targets.storage.get_by_id.assert_any_call(NullMultiTarget, '888', fields={})
		targets.storage.delete.assert_called_once_with(NullMultiTarget, '123')
		referrers.storage.get.assert_called_once_with(NullMultiReferrer, filter={'targets':'123'}, count=False, sort=(), offset=0, limit=0)
		referrers.storage.update.assert_called_once_with(NullMultiReferrer, '666', {'targets':['555', '888']}, replace=False)
		
		
	def test_reverse_delete_cascade(self):
		"""Removing a single linked item with a CASCADE rule, deletes the referencing item"""
		targets = self.get_interface('cascadetargets')
		targets.storage.get_by_id = Mock(return_value={'_id':'123'})
		targets.storage.delete = Mock()
		
		referrers = self.get_interface('cascadereferrers')
		referrers.storage.get = Mock(return_value=[{'_id':'666'}])
		referrers.storage.get_by_id = Mock(return_value={'_id':'666'})
		referrers.storage.check_filter = Mock(return_value=None)
		referrers.storage.delete = Mock()
		
		targets.delete('123')
		
		targets.storage.get_by_id.assert_called_once_with(CascadeTarget, '123')
		targets.storage.delete.assert_called_once_with(CascadeTarget, '123')
		referrers.storage.get.assert_called_once_with(CascadeReferrer, filter={'target':'123'}, count=False, sort=(), offset=0, limit=0)
		referrers.storage.delete.assert_called_once_with(CascadeReferrer, '666')
		