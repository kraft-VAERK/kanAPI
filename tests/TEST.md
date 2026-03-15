# Test Suite

Run all tests (unit + integration, excludes live):
```bash
make test
```

Run live tests only (requires full stack — server, DB, FGA, MinIO):
```bash
uv run pytest tests/test_live.py -v
```

Run a single test:
```bash
uv run pytest tests/path/to/test.py::test_name -v
```

---

## test_case.py — Health (1 test)

| Test | Description |
|------|-------------|
| `test_health_endpoint` | Hits `/health/startup`, `/health/ready`, `/health/live` and asserts 200 |

---

## test_case_activity.py — Case activity log (7 tests)

### `db_log_activity`

| Test | Description |
|------|-------------|
| `test_log_activity_creates_row` | Inserts an activity row; `db_get_case_activities` returns it |
| `test_log_activity_stores_detail` | Detail string is persisted and returned unchanged |
| `test_log_activity_null_user_allowed` | `user_id=None` is accepted (e.g. system events) |

### `db_get_case_activities`

| Test | Description |
|------|-------------|
| `test_get_activities_empty_for_new_case` | Returns empty list when no activity has been logged |
| `test_get_activities_returns_oldest_first` | Multiple entries are returned in ascending `created_at` order |
| `test_get_activities_scoped_to_case` | Activity from one case does not appear in another case's log |
| `test_activity_cascade_deleted_with_case` | Deleting the parent case removes all its activity rows via CASCADE |

---

## test_case_auth.py — Case authorization via OpenFGA (8 tests)

Hierarchy: `superadmin` → `company_a` / `company_b` → `user_a1`, `user_a2`, `user_b1`

### `_get_case_db_or_404`

| Test | Description |
|------|-------------|
| `test_get_case_db_returns_row_when_found` | Returns the CaseDB row when the case ID exists |
| `test_get_case_db_raises_404_when_not_found` | Raises 404 when no case exists for the given ID |

### `require_permission` dependency

| Test | Description |
|------|-------------|
| `test_require_permission_passes_when_fga_allows` | Does not raise when OpenFGA returns `allowed=True` (viewer) |
| `test_require_permission_raises_403_when_fga_denies` | Raises 403 when OpenFGA returns `allowed=False` (viewer) |
| `test_require_permission_editor_passes_when_fga_allows` | Editor permission check passes when OpenFGA allows it |
| `test_require_permission_editor_raises_403_when_fga_denies` | Editor permission check raises 403 when OpenFGA denies it |

### `filter_by_permission`

| Test | Description |
|------|-------------|
| `test_filter_by_permission_returns_allowed_cases` | Only cases the user has viewer access to are returned |
| `test_filter_by_permission_empty_input` | Returns empty list immediately without calling OpenFGA |

---

## test_company.py — Company CRUD and access guards (21 tests)

Hierarchy: `super` → `owner_co` (with `client_a`, `client_b`) + `solo_co`; `cadmin` (company admin); `user1` (regular)

### `db_create_company`

| Test | Description |
|------|-------------|
| `test_create_company_minimal` | Creates a company with only a name; `owner_id` defaults to None |
| `test_create_company_with_owner` | Creates a client company linked to an owner company |
| `test_create_company_with_all_fields` | Creates a company with all optional fields set and verifies they persist |

### `db_get_companies`

| Test | Description |
|------|-------------|
| `test_get_companies_returns_all` | Returns all companies in the database |
| `test_get_companies_empty_after_none_created` | Returns an empty list when no companies exist |

### `db_get_company`

| Test | Description |
|------|-------------|
| `test_get_company_by_id` | Fetches a company by its UUID and verifies the returned name |
| `test_get_company_returns_none_for_missing` | Returns None when the requested company ID does not exist |

### `db_get_client_companies`

| Test | Description |
|------|-------------|
| `test_get_client_companies_returns_children` | Returns only direct client companies owned by the given company |
| `test_get_client_companies_empty_for_leaf` | Returns an empty list for a company that has no client children |

### `_require_super_admin`

| Test | Description |
|------|-------------|
| `test_require_super_admin_passes` | Does not raise for a super admin (`is_admin=True`, `parent_id=None`) |
| `test_require_super_admin_rejects_company_admin` | Raises 403 for a company admin (`is_admin=True` but `parent_id` set) |
| `test_require_super_admin_rejects_regular_user` | Raises 403 for a regular user (`is_admin=False`) |

### `_require_company_admin`

| Test | Description |
|------|-------------|
| `test_require_company_admin_passes` | Does not raise for a company admin (`is_admin=True`, `parent_id` set) |
| `test_require_company_admin_rejects_super_admin` | Raises 403 for a super admin (`parent_id=None` disqualifies company admin role) |
| `test_require_company_admin_rejects_regular_user` | Raises 403 for a regular user (`is_admin=False`) |

### `db_delete_company`

| Test | Description |
|------|-------------|
| `test_delete_company_super_admin_only_passes` | Super admin passes the `_require_super_admin` guard (precondition for delete) |
| `test_delete_company_company_admin_rejected` | Company admin is rejected by `_require_super_admin` and cannot delete a company |
| `test_delete_company_regular_user_rejected` | Regular user is rejected by `_require_super_admin` and cannot delete a company |
| `test_db_delete_company_removes_row` | `db_delete_company` removes the company row and returns `True` |
| `test_db_delete_company_returns_false_for_missing` | Returns `False` when the company ID does not exist |
| `test_db_delete_company_raises_409_when_cases_attached` | Raises 409 Conflict when the company has cases attached |

---

## test_user.py — User CRUD and endpoint guards (12 tests)

Hierarchy: `super_admin` → `company_admin` → `regular_user`

### `db_update_user`

| Test | Description |
|------|-------------|
| `test_db_update_user_changes_username` | Applies partial updates to an existing user |
| `test_db_update_user_returns_none_for_missing_id` | Returns None when the username does not exist |
| `test_db_update_user_hashes_password` | Stores a SHA-256 hash, not the plaintext password |

### `delete_user_by_id`

| Test | Description |
|------|-------------|
| `test_delete_user_non_admin_gets_403` | Non-admin caller gets 403 when attempting to delete any user |
| `test_delete_user_self_delete_gets_400` | Admin gets 400 when trying to delete their own account |
| `test_delete_user_missing_user_gets_404` | Admin gets 404 when the target username does not exist |
| `test_delete_user_success` | Admin can delete another user; the row is removed from the DB |
| `test_company_admin_can_delete_user` | Company admin (`is_admin=True`) can also delete other users |
| `test_delete_user_with_cases_gets_409` | Deleting a user who owns cases returns 409 Conflict |

### `get_user`

| Test | Description |
|------|-------------|
| `test_get_user_non_admin_gets_403` | Non-admin caller gets 403 when trying to view a user profile |
| `test_get_user_missing_gets_404` | Admin gets 404 when the requested username does not exist |
| `test_get_user_success` | Admin can retrieve a user by username and gets the correct data back |

---

## test_live.py — Live integration tests (40 tests)

Requires full stack: `make db && make seed && make run`

### Health

| Test | Description |
|------|-------------|
| `test_health_endpoint` | All three health probes return 200 |
| `test_api_root_returns_welcome` | `GET /` returns a welcome response |
| `test_frontend_build_exists` | Frontend `dist/` build is present and served |

### Authentication

| Test | Description |
|------|-------------|
| `test_login_superadmin` | Super admin can log in and receives a session cookie |
| `test_login_company_admin` | Company admin can log in and receives a session cookie |
| `test_login_wrong_password_returns_401` | Wrong password returns 401 |
| `test_logout_clears_session` | Logout clears the session cookie |
| `test_unauthenticated_case_list_returns_401` | Case list returns 401 without a session |

### Cases

| Test | Description |
|------|-------------|
| `test_create_case_and_fetch_it` | Creating a case returns 201; fetching it by ID returns the same case |
| `test_case_list_returns_only_accessible_cases` | `GET /case/` returns only FGA-permitted cases for the caller |
| `test_create_case_missing_required_field_returns_400` | Missing required field returns 400 |
| `test_creator_can_access_own_case` | Case creator can fetch their own case |
| `test_other_user_without_tuple_gets_403` | User without an FGA tuple gets 403 on another user's case |
| `test_case_not_visible_to_other_company_in_list` | Cross-company case does not appear in the caller's case list |
| `test_nonexistent_case_returns_404` | Non-existent case ID returns 404 |
| `test_creator_can_delete_own_case` | Case creator can delete their own case |
| `test_admin_can_delete_subuser_case` | Company admin can delete a sub-user's case via FGA `deleter` relation |
| `test_delete_case_removes_documents_from_minio` | Deleting a case also removes its documents from MinIO |
| `test_other_company_admin_cannot_delete_case` | Company admin from a different company gets 403 on delete |

### Activity log

| Test | Description |
|------|-------------|
| `test_create_case_logs_case_created` | Creating a case writes a `case_created` activity entry |
| `test_update_case_status_logs_status_changed` | PATCHing status writes a `status_changed` entry with old→new detail |
| `test_update_case_responsible_logs_responsible_changed` | PATCHing `responsible_person` writes a `responsible_changed` entry |
| `test_activity_forbidden_without_viewer_access` | User with no FGA relation to a case gets 403 on the activity endpoint |

### Companies

| Test | Description |
|------|-------------|
| `test_list_companies_authenticated` | Authenticated user can list companies |
| `test_create_company_requires_super_admin` | Non-super-admin gets 403 when creating a company |
| `test_super_admin_can_create_company` | Super admin can create a company; cleans up by deleting it afterwards |
| `test_delete_company_requires_super_admin` | Company admin and regular user get 403 on delete; cleans up in finally |
| `test_delete_company_with_cases_returns_409` | Deleting a company that has cases attached returns 409 Conflict |
| `test_fga_server_is_reachable` | OpenFGA server is up and the configured store exists |

### Documents

| Test | Description |
|------|-------------|
| `test_document_list_for_own_case` | Creator can list documents on their own case |
| `test_company_admin_can_view_documents_on_subuser_case` | Company admin can list documents on a sub-user's case |
| `test_document_download_returns_content` | Downloading a document streams content with the correct content-type |
| `test_document_list_forbidden_for_other_user` | User without FGA access gets 403 on document list |

### Users

| Test | Description |
|------|-------------|
| `test_superadmin_can_get_user_by_id` | Super admin can fetch a user profile by username |
| `test_nonadmin_cannot_get_user_by_id` | Non-admin gets 403 when fetching a user profile |
| `test_superadmin_can_delete_user` | Super admin can delete another user |
| `test_cannot_delete_self` | Admin gets 400 when attempting to delete their own account |
| `test_nonadmin_cannot_delete_user` | Non-admin gets 403 when attempting to delete a user |
| `test_delete_nonexistent_user_returns_404` | Deleting a non-existent username returns 404 |
| `test_delete_user_with_cases_returns_409` | Deleting a user who owns cases returns 409 Conflict |
