from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

import logging

from openid.consumer import consumer
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import ax, pape, sreg
from openid.store.filestore import FileOpenIDStore

logger = logging.getLogger(__name__)

def _get_openid_store():
    return FileOpenIDStore('/tmp/chameleon_openid_c_store')


def _get_consumer(request):
    return consumer.Consumer(request.session, _get_openid_store())

# Create your views here.
def openid_login(request):
    if request.method == 'POST':
        openid_url = request.POST.get('openid_url')
        logger.debug('Attempting OpenID login at %s' % openid_url)
        c = _get_consumer(request)
        try:
            auth_request = c.begin(openid_url)

            sreg_request = sreg.SRegRequest(required=['email', 'nickname'],)
            auth_request.addExtension(sreg_request)

            ax_request = ax.FetchRequest()
            ax_request.add(
                ax.AttrInfo('http://geni.net/projects', required=False, count=ax.UNLIMITED_VALUES)
                )
            ax_request.add(ax.AttrInfo('http://geni.net/prettyname', required=False))
            auth_request.addExtension(ax_request)

            trust_root = request.build_absolute_uri(reverse('chameleon_openid:openid_login'))
            return_to = request.build_absolute_uri(reverse('chameleon_openid:openid_callback'))
            url = auth_request.redirectURL(trust_root, return_to)
            return HttpResponseRedirect(url)

        except DiscoveryFailure, e:
            logger.error("OpenID discovery error: %s" % (str(e),))

    context = {
        'providers': settings.OPENID_PROVIDERS
    }

    return render(request, 'chameleon_openid/login.html', context)


def openid_callback(request):

    logger.info(request.GET)
    logger.info(request.POST)

    pass