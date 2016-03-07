## Changelog

### v1.11.0

- Fixed permissions issue for users editing own appliances
- Updated project request requirements
- Updated Nginx configuration

### v1.10.0

- New appliance marketplace
- Fix bug with creating new allocations on existing projects
- Fix OpenID CSRF

### v1.9.0

- Improved allocation request workflow
- Updated allocation request form instructions
- Updated help desk categories

### v1.8.1

- New Table of Contents style
  - ToC can be configured as "sidebar" or "header"

### v1.8.0

- Table of Contents for Docuementation
  - Generate a ToC for html content by embedding the CMS placeholders in a
    Style element with the "Enable TOC" class name
- Updated allocation renewals to allow a "recharge and extend" at any time
- Added phone number to profile, registration form

### v1.7.1

- Fix template bug with GENI/OpenID Registration

### v1.7.0

- GENI OpenID Authentication and Project Federation

### v1.6.4

- Add project counts to admin pages
- Fix usage rendering (percentages were 0..1 instead of 0..100)

### v1.6.3

- Fix password policy check bug on registration form
- Display "date requested" on pending allocations
- Fix bug where "submit renewal" button shown on a pending allocation after submitting the renewal
- Update allocation forms
- Automatically create a ticket when a user submits a PI request

### v1.6.1

- Logging
- Better error pages
- Fix password policy checks
- Performance instrumentation

### v1.6.0

- Closing a ticket now requires a comment #6874
- Fixed missing dates for admin allocation approval #7865
- Improved logging of allocation admin actions #7863
- Completely refactored Resource Discovery #7683
- Record supplemental details and funding sources in allocation justification instead of project description #8007
- Added detailed allocation display, usage reporting, renewal support #7811
- Deprecate FutureGrid@Chameleon transitional support #

### v1.5.6

- limit `user.title` to 50 characters
- improved logging during registration process

### v1.5.5

- Update help desk ticket categories #7866
- Update "Users" menu items #7889

### v1.5.4

- Registration form validation fixes #7930

### v1.5.3

- fix field name for new insitutions on registration

### v1.5.2

- fix reverse URLs for django-termsandconditions

### v1.5.1

- update pi eligibility notes in form help

### v1.5.0

- Fix bug with filters "approved/active" in admin allocation approval
- remove "futuregrid@chameleon" menu/references
- add terms of use links to account page
- update tas profile, registration views to use forms
- added djangocms-cascade
- updated projects form for additional fields, request config
- additional updates to prepare for public release
- CMS pages no longer preserve the parent link. Parent pages are placeholders only.

### v1.4.1

- update PI eligibility policy for new account registration

### v1.4.0

-

### v1.3.4

- EUP export support for either UID or email exports

### v1.3.3

- Update Early User Program Participant message with link to CMS page with ID 'early_users_guide'. This requires a page to exist in the CMS with that ID (set under Advanced Settings) or the template render will error.

### v1.3.2

- Added export similar to mailing list export for early user participants

### v1.3.1

- Improvements
  - Fix error for mailing list management for new users since 1.3.0
  - Fix mailing list exports to correctly default to "subscribed"

### v1.3.0

- New Features
  - Manage TAS User Accounts from Django Admin
    - Trigger Password Reset
    - Manage PI Eligibility
    - Edit User Profiles (name, email address, etc.)
  - User News "Outages" view
  - Email Subscriptions
    - Users can control what email lists they would like to be subscribed to
    - List export for ingestion into external email listserv
- Code style improvements

### v1.2.5

- Add RSS item_pubdate
- Address string formatting issue with tickets

### v1.2.4

- Add RSS feed for news/announcements
- Add category field for tickets
- Don't display the "untitled" attachments from RT, which is just the ticket/reply content
- Add /robots.txt

### v1.2.3

- Add ability to request PI Eligibility from profile edit page
- Added admin functionality

### v1.2.2

- G5K Discovery fixes

### v1.2.1

- Added early user program app `cc_early_user_support`
- Removed `.deprecated_apps`
- `docker-compose.yml` included with repo configured for development work right away
- Documented Docker Compose use
- Moved Django logs from `/tmp` to `/var/log/django` (inside container).
- G5K discovery fixes

### v1.2.0

- Add DjangoCMS
- New User News app to replace the old github_content app
- G5K Resource Discovery UI
- Added docker-compose to orchestrate launching both the portal and the [reference-api][1] containers
- Squashed bugs

### v1.1.2

- Fix new institution creation when not listed

### v1.1.1

- Fixed documentation errors

### v1.1.0

- Added PI eligibility at registration and new project creation

### v1.0.1

- Improve workflow for FG project migration

### v1.0.0

- Initial release


[1]: https://github.com/ChameleonCloud/reference-api
