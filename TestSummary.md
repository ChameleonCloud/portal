# Lists of tests that do not work:
```
ERROR: test_allocation_form_fields_required (projects.tests.ProjectViewTests)
Tests that appropriate fields are required on the project form.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1346, in patched
    return func(*newargs, **newkeywargs)
  File "/project/projects/tests.py", line 227, in test_allocation_form_fields_required
    mock_tas_project.return_value = json.loads(f.read())
  File "/usr/local/lib/python3.7/json/__init__.py", line 348, in loads
    return _default_decoder.decode(s)
  File "/usr/local/lib/python3.7/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
  File "/usr/local/lib/python3.7/json/decoder.py", line 353, in raw_decode
    obj, end = self.scan_once(s, idx)
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 106 column 1 (char 2953)
```
```
ERROR: test_project_form_fields_required (projects.tests.ProjectViewTests)
Tests that appropriate fields are required on the project form.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/keycloak/client.py", line 84, in _handle_response
    response.raise_for_status()
  File "/usr/local/lib/python3.7/site-packages/requests/models.py", line 1021, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 401 Client Error: Unauthorized for url: https://auth.dev.chameleoncloud.org/auth/realms/master/protocol/openid-connect/token
```
```
======================================================================
ERROR: test_view_allocation_rejected (projects.tests.ProjectViewTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/utils.py", line 84, in _execute
    return self.cursor.execute(sql, params)
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/mysql/base.py", line 73, in execute
    return self.cursor.execute(query, args)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 209, in execute
    res = self._query(query)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 315, in _query
    db.query(q)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/connections.py", line 239, in query
    _mysql.connection.query(self, query)
MySQLdb._exceptions.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`chameleon_dev_test`.`cms_pageuser`, CONSTRAINT `cms_pageuser_created_by_id_18eb7aa0ce6f1c16_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`))')
```
```
ERROR: test_view_allocation_rejected_with_active (projects.tests.ProjectViewTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/utils.py", line 84, in _execute
    return self.cursor.execute(sql, params)
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/mysql/base.py", line 73, in execute
    return self.cursor.execute(query, args)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 209, in execute
    res = self._query(query)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 315, in _query
    db.query(q)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/connections.py", line 239, in query
    _mysql.connection.query(self, query)
MySQLdb._exceptions.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`chameleon_dev_test`.`cms_pageuser`, CONSTRAINT `cms_pageuser_created_by_id_18eb7aa0ce6f1c16_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`))')
```
```
ERROR: test_view_project (projects.tests.ProjectViewTests)
Test that a project with an active allocation up for renewal displays the recharge
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/utils.py", line 84, in _execute
    return self.cursor.execute(sql, params)
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/mysql/base.py", line 73, in execute
    return self.cursor.execute(query, args)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 209, in execute
    res = self._query(query)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 315, in _query
    db.query(q)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/connections.py", line 239, in query
    _mysql.connection.query(self, query)
MySQLdb._exceptions.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`chameleon_dev_test`.`cms_pageuser`, CONSTRAINT `cms_pageuser_created_by_id_18eb7aa0ce6f1c16_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`))')
```
```
ERROR: test_view_project_redirect (projects.tests.ProjectViewTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/utils.py", line 84, in _execute
    return self.cursor.execute(sql, params)
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/mysql/base.py", line 73, in execute
    return self.cursor.execute(query, args)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 209, in execute
    res = self._query(query)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 315, in _query
    db.query(q)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/connections.py", line 239, in query
    _mysql.connection.query(self, query)
MySQLdb._exceptions.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`chameleon_dev_test`.`cms_pageuser`, CONSTRAINT `cms_pageuser_created_by_id_18eb7aa0ce6f1c16_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`))')
```
```
ERROR: test_view_project_with_pending (projects.tests.ProjectViewTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/utils.py", line 84, in _execute
    return self.cursor.execute(sql, params)
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/mysql/base.py", line 73, in execute
    return self.cursor.execute(query, args)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 209, in execute
    res = self._query(query)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 315, in _query
    db.query(q)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/connections.py", line 239, in query
    _mysql.connection.query(self, query)
MySQLdb._exceptions.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`chameleon_dev_test`.`cms_pageuser`, CONSTRAINT `cms_pageuser_created_by_id_18eb7aa0ce6f1c16_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`))')
```
```
ERROR: test_edit_profile_submit (tas.tests.EditProfileViewTests)
POSTing the form on the edit profile page should call TASClient.save_user. Also,
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/utils.py", line 84, in _execute
    return self.cursor.execute(sql, params)
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/mysql/base.py", line 73, in execute
    return self.cursor.execute(query, args)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 209, in execute
    res = self._query(query)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 315, in _query
    db.query(q)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/connections.py", line 239, in query
    _mysql.connection.query(self, query)
MySQLdb._exceptions.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`chameleon_dev_test`.`cms_pageuser`, CONSTRAINT `cms_pageuser_created_by_id_18eb7aa0ce6f1c16_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`))')
```
```
ERROR: test_edit_profile_view (tas.tests.EditProfileViewTests)
Logged in users can access the edit profile view.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/utils.py", line 84, in _execute
    return self.cursor.execute(sql, params)
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/mysql/base.py", line 73, in execute
    return self.cursor.execute(query, args)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 209, in execute
    res = self._query(query)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 315, in _query
    db.query(q)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/connections.py", line 239, in query
    _mysql.connection.query(self, query)
MySQLdb._exceptions.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`chameleon_dev_test`.`cms_pageuser`, CONSTRAINT `cms_pageuser_created_by_id_18eb7aa0ce6f1c16_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`))')
```
```
ERROR: test_edit_profile_view_source_not_chameleon (tas.tests.EditProfileViewTests)
User accounts sourced from places other than Chameleon cannot edit their profile
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/utils.py", line 84, in _execute
    return self.cursor.execute(sql, params)
  File "/usr/local/lib/python3.7/site-packages/django/db/backends/mysql/base.py", line 73, in execute
    return self.cursor.execute(query, args)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 209, in execute
    res = self._query(query)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/cursors.py", line 315, in _query
    db.query(q)
  File "/usr/local/lib/python3.7/site-packages/MySQLdb/connections.py", line 239, in query
    _mysql.connection.query(self, query)
MySQLdb._exceptions.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`chameleon_dev_test`.`cms_pageuser`, CONSTRAINT `cms_pageuser_created_by_id_18eb7aa0ce6f1c16_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`))')
```
```
ERROR: test_register_view (tas.tests.RegisterViewTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1345, in patched
    keywargs) as (newargs, newkeywargs):
  File "/usr/local/lib/python3.7/contextlib.py", line 112, in __enter__
    return next(self.gen)
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1325, in decoration_helper
    arg = exit_stack.enter_context(patching)
  File "/usr/local/lib/python3.7/contextlib.py", line 427, in enter_context
    result = _cm_type.__enter__(cm)
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1414, in __enter__
    original, local = self.get_original()
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1388, in get_original
    "%s does not have the attribute %r" % (target, name)
AttributeError: <module 'tas.forms' from '/project/tas/forms.py'> does not have the attribute 'get_institution_choices'
```
```ERROR: test_register_view_submit_not_pi (tas.tests.RegisterViewTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1345, in patched
    keywargs) as (newargs, newkeywargs):
  File "/usr/local/lib/python3.7/contextlib.py", line 112, in __enter__
    return next(self.gen)
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1325, in decoration_helper
    arg = exit_stack.enter_context(patching)
  File "/usr/local/lib/python3.7/contextlib.py", line 427, in enter_context
    result = _cm_type.__enter__(cm)
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1414, in __enter__
    original, local = self.get_original()
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1388, in get_original
    "%s does not have the attribute %r" % (target, name)
AttributeError: <module 'tas.forms' from '/project/tas/forms.py'> does not have the attribute 'get_institution_choices'
```
```
ERROR: test_register_view_submit_pi (tas.tests.RegisterViewTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1345, in patched
    keywargs) as (newargs, newkeywargs):
  File "/usr/local/lib/python3.7/contextlib.py", line 112, in __enter__
    return next(self.gen)
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1325, in decoration_helper
    arg = exit_stack.enter_context(patching)
  File "/usr/local/lib/python3.7/contextlib.py", line 427, in enter_context
    result = _cm_type.__enter__(cm)
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1414, in __enter__
    original, local = self.get_original()
  File "/usr/local/lib/python3.7/site-packages/mock/mock.py", line 1388, in get_original
    "%s does not have the attribute %r" % (target, name)
AttributeError: <module 'tas.forms' from '/project/tas/forms.py'> does not have the attribute 'get_institution_choices'
```
```
ERROR: sharing_portal.tests.test_artifact (unittest.loader._FailedTest)
----------------------------------------------------------------------
ImportError: Failed to import test module: sharing_portal.tests.test_artifact
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/unittest/loader.py", line 436, in _find_test_path
    module = self._get_module_from_name(name)
  File "/usr/local/lib/python3.7/unittest/loader.py", line 377, in _get_module_from_name
    __import__(name)
  File "/project/sharing_portal/tests/test_artifact.py", line 7, in <module>
    from .. import DEV as dev
ImportError: cannot import name 'DEV' from 'sharing_portal' (/project/sharing_portal/__init__.py)
```
```
ERROR: sharing_portal.tests.test_views (unittest.loader._FailedTest)
----------------------------------------------------------------------
ImportError: Failed to import test module: sharing_portal.tests.test_views
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/unittest/loader.py", line 436, in _find_test_path
    module = self._get_module_from_name(name)
  File "/usr/local/lib/python3.7/unittest/loader.py", line 377, in _get_module_from_name
    __import__(name)
  File "/project/sharing_portal/tests/test_views.py", line 8, in <module>
    from ..views import make_author, upload_artifact
ImportError: cannot import name 'make_author' from 'sharing_portal.views' (/project/sharing_portal/views.py)
```