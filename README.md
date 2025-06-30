# Django-Keycloak Integration

### Main Settings Configuration

```python
KEYCLOAK_SERVER_URL = config('KEYCLOAK_SERVER_URL', default="http://localhost:8080", cast=str)
KEYCLOAK_ISSUER_PREFIX = config('KEYCLOAK_ISSUER_PREFIX', default="http://localhost:8080", cast=str)
KEYCLOAK_REALM = config('KEYCLOAK_REALM', cast=str)
KEYCLOAK_CLIENT_ID = config('KEYCLOAK_CLIENT_ID', cast=str)
KEYCLOAK_CLIENT_TITLE = config('KEYCLOAK_CLIENT_TITLE', cast=str)
KEYCLOAK_CLIENT_NAME = config('KEYCLOAK_CLIENT_NAME', cast=str)
KEYCLOAK_CLIENT_SECRET = config('KEYCLOAK_CLIENT_SECRET', cast=str)
KEYCLOAK_ALGORITHMS = config('KEYCLOAK_ALGORITHMS', cast=str, default='RS256')
KEYCLOAK_OAUTH_REDIRECT_URI = config(
    'KEYCLOAK_OAUTH_REDIRECT_URI',
    default="http://127.0.0.1:8000/auth/callback/",
    cast=str
)
KEYCLOAK_DEFAULT_ADMIN_PANEL_PERMISSION_CLASSES = [
    'django_keycloak_sso.permissions.IsAuthenticatedAccess'
] # default permission to access keycloak admin data endpoints
```

examples:

```python
KEYCLOAK_SERVER_URL=https://sso.domain # if using in dokcer : https://<keycloak_container>:8443
KEYCLOAK_ISSUER_PREFIX=https://sso.domain
KEYCLOAK_REALM=main
KEYCLOAK_CLIENT_ID=ecommerce-back
KEYCLOAK_CLIENT_SECRET=<client_secret_key>
KEYCLOAK_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/auth/callback/ # for login in ssr sites
KEYCLOAK_CLIENT_NAME=ecommerce
KEYCLOAK_CLIENT_TITLE=ecommerce-back
KEYCLOAK_ALGORITHMS=RS256
```

---

### Authentication and Middlewares class usage

Mock default django or DRF authentication proccess

you can access to user in views like :

```python
user = request.user
user.id
user.username
```

- KeycloakAuthentication

- KeycloakMiddleware
  
  ```python
  REST_FRAMEWORK = {
      'DEFAULT_AUTHENTICATION_CLASSES': [
          'django_keycloak_sso.middlewares.KeycloakAuthentication',
      ]
  } # Usable for DRF services
  
  MIDDLEWARE = [
      'django_keycloak_sso.middlewares.KeycloakMiddleware',
  ] # Usable for SSR websites
  ```

note : **KeycloakAuthentication** is enough for DRF backend services



### User Attrs and Properties

**request.user** is a instance of **<u>CustomUser</u>** class with these properties :

- groups  

- groups_dict_list  

- groups_parent  

- group_roles  

- realm_roles  

- client_roles  

- roles  

- id  

- username  

- first_name  

- last_name  

- full_name  

- groups_id

- All other keycloak user properties ...

---

### Permission Decorators

These decorators provide fine-grained access control for your views using Keycloak user attributes. They can be used on Django views, DRF APIViews, or function-based views. All decorators rely on the check_user_permission_access function internally.

    All decorators are stackable — combine multiple for more specific permission control.

#### Available Decorators

```python
from django_keycloak_sso.decorators import (
    require_roles,
    require_groups,
    require_group_roles,
    require_all_permissions
)
```

**@require_roles(\*role_titles)**

Checks if the user has all of the specified realm or client roles.
```python
@require_roles('superuser', 'admin')
def view_func(request):
    pass
```

**@require_groups(\*group_titles)**

Checks if the user is a member of all specified group names.
```python
@require_groups('group_1')
def view_func(request):
    pass
```

**@require_group_roles(\*group_roles, match_group_roles=False)**

Checks if the user has at least one of the specified roles within any group.
Use **match_group_roles=True** to only allow matches where the group name is also explicitly listed via @require_groups.

```python
@require_group_roles('manager')  # Any group
@require_group_roles('admin', match_group_roles=True)  # Must match both group and role
def view_func(request):
    pass
```

**@require_all_permissions(role_titles=[], group_titles=[], group_roles=[], match_group_roles=False)**

Combined decorator that allows you to check all types of permissions in one call.

```python
@require_all_permissions(
    role_titles=['superuser'],
    group_titles=['group_1'],
    group_roles=['manager'],
    match_group_roles=True
)
def view_func(request):
    pass
```

#### Stacking Decorators

You can combine decorators for more control:

```python
@require_roles('superuser')
@require_groups('group_1')
@require_group_roles('manager')
def view_func(request):
    pass
```

    All decorators raise PermissionDenied (403) if access checks fail.
    Make sure your view expects an authenticated user (request.user.is_authenticated is checked internally).

---

### Permission Classes

- IsManagerAccess

- IsSuperUserAccess

- IsSuperUserOrManagerAccess

#### Usage Examples

```python
class TestView(APIView):
    http_method_names = ('get',)
    permission_classes = (IsManagerAccess,) 
```

---

### Predefined Model, Meta Class, Fields

- SSOModelMeta

- CustomMetaSSOModelSerializer

- SSOGroupField

- SSOUserField

- SSOManyUserField

- SSOManyGroupField

- SSOManyField
  
  
  
  

#### Usage Examples

```python
from django_keycloak_sso.sso import fields as sso_fields
from django_keycloak_sso.sso.meta import CustomMetaSSOModelSerializer, SSOModelMeta 


class Server(Model, metaclass=SSOModelMeta):
    user = sso_fields.SSOUserField(verbose_name=_("User"))
    group_id = sso_fields.SSOGroupField(verbose_name=_("Group"))
    delivery_users = sso_fields.SSOManyUserField(verbose_name=_("Delivery Users")) # New Many-to-Many Field

class ServerSerializer(CustomMetaSSOModelSerializer):
  # is limited : get ids or full data of assigned instances
  delivery_users = SSOManyField(source='delivery_users', field_type='user', is_limited=True) # New Many-to-Many Serializer Field
    class Meta:
        model = Server
        fields = (...)    
```



### Benefits of using **<u>SSOModelMeta</u>** and  <u>**SSO Fields**</u>:

- access to sso field data
  
  ```python
  mode_obj.fieldname_data # mock django relation fields behavior
  my_server.user_data # get a dict of user datas
  my_server.user_data.username # get a key from sso field data
  my_server.delivery_users.get_ids # get ids of saved m2m instances
  my_server.delivery_users.get_full_data # get full datas of saved m2m instances
  my_server.delivery_users.add # add an instance to m2m field
  my_server.delivery_users.remove # remove an instance to m2m field
  
  # NOTE : Do same with group fields
  ```

- auto validation field object exists in keycloak
  
  when using CustomMetaSSOModelSerializer in a serializer and wants to create a instance with that serializer. it will automatically validate existence of data in keycloak and if not return proportionate error.

---

### Define Endpoints

```python
urlpatterns = [
    path('accounts/', include('django_keycloak_sso.urls')),
]
```

##### Endpoints List

- /v1/auth/login/ 

- /v1/auth/refresh/

- /v1/auth/logout/

- /v1/sso/profile/

- /v1/sso/groups/

- /v1/sso/groups/<group_id>/

- /v1/sso/users/

- /v1/sso/users/<user_id>/

**Note :** for more information about how to use them, check created swagger for your project

---

### Usefull Utilities

**get_serializer_field_data**

> ```python
>     from django_keycloak_sso.sso.sso import SSOKlass
> 
>     sso_klass = SSOKlass()
>     
>     class TestSerializer(ModelSerializer):
>         user_data = SerializerMethodField()
>     
>        def __init__(self, *args, **kwargs):
>             super().__init__(*args, **kwargs)
>             queryset = args[0] if len(args) >= 1 else None
>             self.user_list_data = list()
>         
>             if queryset and (isinstance(queryset, QuerySet) or isinstance(queryset, list)):
>                 self.user_list_data = sso_klass.get_sso_data_list(
>                     queryset,
>                     'user', # field name defined in model
>                     sso_klass.SSOFieldTypeChoices.USER
>                 )
> 
>         def get_user_data(self, obj) -> dict | None:
>             return sso_klass.get_serializer_field_data(
>                 field_name='user', # field name defined in model
>                 field_type=sso_klass.SSOFieldTypeChoices.USER, # Or GROUP
>                 obj_=obj,
>                 list_data=self.user_list_data, # Optional for optimize list data caching
>                 get_from_list=True # True if you want use <list_data>
>             )
> ```



**send_request**

integration with keycloak

> ```python
> keycloak_klass = KeyCloakConfidentialClient()
> users_data = keycloak_klass.send_request(
>             self.keycloak_klass.KeyCloakRequestTypeChoices.USER_ROLES, # has many options to integrate with keycloak
>             self.keycloak_klass.KeyCloakRequestTypeChoices,
>             self.keycloak_klass.KeyCloakRequestMethodChoices.GET,
>             self.keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
>             detail_pk='1234', # Additional data args
>             extra_headers={} #Additional request headers
>         )
> ```

---

### Advanced Usage

For get more facilities and features go deep on these classes :

- SSOKlass

- SSOCacheControlKlass

- KeyCloakBaseManager

- KeyCloakConfidentialClient

- KeyCloakInitializer

- BaseKeycloakAdminView

- CustomSSORelatedField

**Note:** To get most caching performance use REDIS as cache system (especially HiRedis)

---
