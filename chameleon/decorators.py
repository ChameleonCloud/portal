"""View Decorators for termsandconditions module"""
import urllib.parse
from functools import wraps
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.http import HttpResponseRedirect, QueryDict
from django.utils.decorators import available_attrs
from termsandconditions.models import TermsAndConditions, UserTermsAndConditions

def terms_required(terms_slug):
    def decorator(view_func):
        """
        This decorator checks to see if the user is logged in, and if so, if they have accepted the site terms.
        """

        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            """Method to wrap the view passed in"""

            terms = TermsAndConditions.objects.filter(slug=terms_slug)[0]
            if not request.user.is_authenticated() or _agreed_to_terms( request.user, terms ):
                return view_func(request, *args, **kwargs)

            currentPath = request.META['PATH_INFO']
            accept_path = reverse('tc_accept_specific_version_page', args=[terms.slug, terms.version_number])
            login_url_parts = list(urllib.parse.urlparse(accept_path))
            querystring = QueryDict(login_url_parts[4], mutable=True)
            querystring['returnTo'] = currentPath
            login_url_parts[4] = querystring.urlencode(safe='/')
            return HttpResponseRedirect(urllib.parse.urlunparse(login_url_parts))

        return _wrapped_view
    return decorator

def _agreed_to_terms( user, terms ):
    try:
        UserTermsAndConditions.objects.get(user=user, terms=terms)
        return True
    except UserTermsAndConditions.MultipleObjectsReturned:
        return True
    except UserTermsAndConditions.DoesNotExist:
        return False

def anonymous_required(function=None, redirect_url='/'):
    """
    Decorator for views that checks that the user is NOT logged in, redirecting
    to the specified page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_anonymous(),
        login_url=redirect_url
    )

    if function:
        return actual_decorator(function)
    return actual_decorator
