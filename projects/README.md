# Publication Collection and Analysis

A subset of this projects django app is used for publication analysis.

## Collection

The `./user_publication/publications.py:import_pubs` function is the main entrypoint for automatic publication collection.
The `./user_publication/` directory contains files for pulling pubs from Scopus, Semantic Scholar, OpenAlex, and Science Direct.

Users and admins can submit bibtex via `forms.py:AddBibtexPublicationForm`. Admins do this on the admin page from google scholar
library exports.

## Review

We review publications using the admin panel. See `./admin.py` for some custom form fields that we add to make this process easier.

See `./user_publication/utils.py` for how we find similar publications for reviewers to check during this process.


