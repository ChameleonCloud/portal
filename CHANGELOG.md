## Changelog

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
