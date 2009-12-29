from httplib import BadStatusLine
from urllib2 import URLError

from zope import component
from zope.app.component.hooks import getSite
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.publisher.browser import BrowserPage
from zope.session.interfaces import ISession
from zope.traversing.browser import absoluteURL

from zojax.principal.twitter import oauthtwitter
from zojax.principal.twitter.interfaces import _
from zojax.principal.twitter.plugin import SESSION_KEY, REQUEST_TOKEN_KEY
from zojax.controlpanel.interfaces import IConfiglet
from zojax.statusmessage.interfaces import IStatusMessage


class TwitterSignIn(BrowserPage):

    def __call__(self):
        if not IUnauthenticatedPrincipal.providedBy(self.request.principal):
            self._redirectToRoot()
            return u''
        configlet = component.getUtility(IConfiglet, name="product.zojax-authentication-twitter")
        consumerKey = configlet.consumerKey
        consumerSecret = configlet.consumerSecret
        if not consumerKey or not consumerSecret:
            self._redirectToRoot()
            return u''
        twitter = oauthtwitter.OAuthApi(consumerKey, consumerSecret)
        try:
            requestToken = twitter.getRequestToken()
            session = ISession(self.request)[SESSION_KEY]
            session[REQUEST_TOKEN_KEY] = requestToken
            url = twitter.getSigninURL(requestToken)
        except (BadStatusLine, URLError):
            message = IStatusMessage(self.request)
            message.add(_(u"Can't connect to Twitter server. Try again later."), "error")
            self._redirectToRoot()
            return u''
        self.request.response.redirect(url)
        return u''

    def _redirectToRoot(self):
        self.request.response.redirect(absoluteURL(getSite(), self.request))
