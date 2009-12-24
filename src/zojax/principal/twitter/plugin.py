import rwproperty
import traceback
from httplib import BadStatusLine
from urllib2 import HTTPError, URLError

from zope import interface, component, event
from zope.app.authentication.interfaces import IAuthenticatorPlugin
from zope.app.container.interfaces import DuplicateIDError, INameChooser
from zope.app.security.interfaces import IAuthentication, PrincipalLookupError
from zope.cachedescriptors.property import Lazy
from zope.exceptions.interfaces import UserError
from zope.schema.fieldproperty import FieldProperty
from zope.security.management import queryInteraction
from zope.session.interfaces import ISession

from zojax.authentication.factory import CredentialsPluginFactory, \
    AuthenticatorPluginFactory
from zojax.authentication.interfaces import ICredentialsPlugin, \
    PrincipalRemovingEvent, IPrincipalInfoStorage
from zojax.authentication.nocachingstorage import NoCachingStorage
from zojax.principal.twitter import oauthtwitter
from zojax.principal.twitter.interfaces import ITwitterPrincipal, _, \
    ITwitterCredentials, ITwitterAuthenticator
from zojax.cache.interfaces import ICacheConfiglet
from zojax.content.type.container import ContentContainer
from zojax.content.type.item import PersistentItem
from zojax.controlpanel.interfaces import IConfiglet
from zojax.principal.users.interfaces import IUsersPlugin
from zojax.principal.users.plugin import PrincipalInfo


SESSION_KEY = 'zojax.authentication.twitter'
REQUEST_TOKEN_KEY = '_twitter_request_token'
ACCESS_TOKEN_KEY = '_twitter_access_token'


_marker = object()


def getRequest():
    interaction = queryInteraction()

    if interaction is not None:
        for participation in interaction.participations:
            return participation


class TwitterPrincipal(PersistentItem):
    interface.implements(ITwitterPrincipal)

    firstname = FieldProperty(ITwitterPrincipal['firstname'])
    lastname = FieldProperty(ITwitterPrincipal['lastname'])
    login = FieldProperty(ITwitterPrincipal['login'])
    password = FieldProperty(ITwitterPrincipal['password'])
    description = FieldProperty(ITwitterPrincipal['description'])
    twitterId = FieldProperty(ITwitterPrincipal['twitterId'])

    @rwproperty.getproperty
    def title(self):
        return (u'%s %s'%(self.firstname, self.lastname)).strip()

    @rwproperty.setproperty
    def title(self, title):
        names = title.split(None, 1)
        if len(names) == 1:
            self.firstname, self.lastname = (names[0], u'')
        else:
            self.firstname, self.lastname = names

    @Lazy
    def id(self):
        self.id = '%s%s%s'%(
            component.getUtility(IAuthentication, context=self).prefix,
            self.__parent__.prefix, self.__name__)
        return self.id

    def getLogin(self):
        return self.login


class TwitterCredentials(object):
    interface.implements(ITwitterCredentials)

    def __init__(self, requestToken=None, accessToken=None):
        self.requestToken = requestToken
        self.accessToken = accessToken


class CredentialsPlugin(PersistentItem):
    interface.implements(ICredentialsPlugin)

    def __init__(self, title=u'', description=u''):
        self.title = title
        self.description = description

    def extractCredentials(self, request):
        """Ties to extract credentials from a request.

        A return value of None indicates that no credentials could be found.
        Any other return value is treated as valid credentials.
        """
        session = ISession(request)[SESSION_KEY]
        requestToken = session.get(REQUEST_TOKEN_KEY)
        accessToken = session.get(ACCESS_TOKEN_KEY)
        if not requestToken and not accessToken:
            return None
        return TwitterCredentials(requestToken, accessToken)


class AuthenticatorPlugin(ContentContainer):
    interface.implements(IUsersPlugin, IAuthenticatorPlugin, ITwitterAuthenticator, INameChooser)

    def __init__(self, title=_('Twitter users'), description=u'', prefix=u'zojax.twitter.'):
        self.prefix = unicode(prefix)
        self.__name_chooser_counter = 1
        self.__id_by_login = self._newContainerData()
        self.__id_by_twitter_id = self._newContainerData()
        super(AuthenticatorPlugin, self).__init__(title=title, description=description)

    def _getTwitterUser(self, accessToken):
        configlet = component.getUtility(IConfiglet, context=self, name="product.zojax-authentication-twitter")
        consumerKey = configlet.consumerKey
        consumerSecret = configlet.consumerSecret
        if not consumerKey or not consumerSecret:
            return None
        cache = component.getUtility(ICacheConfiglet, context=self)
        ob = ('zojax.authentication.twitter', '_getTwitterUser')
        key = {'accessToken': accessToken}
        result = cache.query(ob, key, _marker)
        if result is _marker:
            twitter = oauthtwitter.OAuthApi(consumerKey, consumerSecret, accessToken)
            try:
                result = twitter.GetUserInfo()
            except (BadStatusLine, URLError):
                return None
            cache.set(result, ob, key)
        return result

    def _createPrincipal(self, twitterUser):
        principal = TwitterPrincipal()
        principal.login = unicode(twitterUser.screen_name, 'utf-8')
        principal.password = u''
        principal.title = unicode(twitterUser.name, 'utf-8')
        principal.description = unicode(twitterUser.description, 'utf-8')
        principal.twitterId = twitterUser.id
        return principal

    def authenticateCredentials(self, credentials):
        """Authenticates credentials.

        If the credentials can be authenticated, return an object that provides
        IPrincipalInfo. If the plugin cannot authenticate the credentials,
        returns None.
        """
        if not ITwitterCredentials.providedBy(credentials):
            return None

        try:
            requestToken = credentials.requestToken
            accessToken = credentials.accessToken
            if requestToken and not accessToken:
                configlet = component.getUtility(IConfiglet, name="product.zojax-authentication-twitter")
                consumerKey = configlet.consumerKey
                consumerSecret = configlet.consumerSecret
                twitter = oauthtwitter.OAuthApi(consumerKey, consumerSecret, requestToken)
                accessToken = twitter.getAccessToken()
                session = ISession(getRequest())[SESSION_KEY]
                auth = component.getUtility(IAuthentication, context=self)
                storage = IPrincipalInfoStorage(auth, None)
                if storage is None or isinstance(storage, NoCachingStorage):
                    # No caching storage is used. Save access token in session
                    # so we don't have to re-request it again.
                    session[ACCESS_TOKEN_KEY] = accessToken
                del session[REQUEST_TOKEN_KEY]

            if accessToken:
                twitterUser = self._getTwitterUser(accessToken)
                if twitterUser is None:
                    return None
                principalId = self.getPrincipalByTwitterId(twitterUser.id)
                if principalId is None:
                    # Principal does not exist.
                    principal = self._createPrincipal(twitterUser)
                    name = INameChooser(self).chooseName('', principal)
                    self[name] = principal
                    principalId = self.getPrincipalByTwitterId(principal.twitterId)
                return self.principalInfo(self.prefix + principalId)

            return None
        except HTTPError, error:
            if error.code == "401":
                logger.warning("Failed to authenticate in Twitter.")
                return None
        except (BadStatusLine, URLError):
            return None
        except:
            logger.error(traceback.format_exc())
            raise

    def principalInfo(self, id):
        """Returns an IPrincipalInfo object for the specified principal id.

        If the plugin cannot find information for the id, returns None.
        """
        if id.startswith(self.prefix):
            internal = self.get(id[len(self.prefix):])
            if internal is not None:
                return PrincipalInfo(id, internal)

    def getPrincipalByLogin(self, login):
        """ return principal info by login """
        if login in self.__id_by_login:
            return self.__id_by_login.get(login)

    def getPrincipalByTwitterId(self, twitterId):
        if twitterId in self.__id_by_twitter_id:
            return self.__id_by_twitter_id.get(twitterId)

    def checkName(self, name, object):
        if not name:
            raise UserError("An empty name was provided. Names cannot be empty.")

        if isinstance(name, str):
            name = unicode(name)
        elif not isinstance(name, unicode):
            raise TypeError("Invalid name type", type(name))

        if not name.isdigit():
            raise UserError("Name must consist of digits.")

        if name in self:
            raise UserError("The given name is already being used.")

        return True

    def chooseName(self, name, object):
        while True:
            name = unicode(self.__name_chooser_counter)
            try:
                self.checkName(name, object)
                return name
            except UserError:
                self.__name_chooser_counter += 1

    def __setitem__(self, id, principal):
        # A user with the new login already exists
        login = principal.login
        if login in self.__id_by_login:
            raise DuplicateIDError('Principal Login already taken!, ' + login)

        super(AuthenticatorPlugin, self).__setitem__(id, principal)
        self.__id_by_login[principal.login] = id
        self.__id_by_twitter_id[principal.twitterId] = id

    def __delitem__(self, id):
        # notify about principal removing
        auth = component.queryUtility(IAuthentication)
        if auth is not None:
            pid = auth.prefix + self.prefix + id
            try:
                principal = auth.getPrincipal(pid)
                event.notify(PrincipalRemovingEvent(principal))
            except PrincipalLookupError:
                pass

        # actual remove
        principal = self[id]
        super(AuthenticatorPlugin, self).__delitem__(id)
        del self.__id_by_login[principal.login]
        del self.__id_by_twitter_id[principal.twitterId]


credentialsFactory = CredentialsPluginFactory(
    "credentials.twitter", CredentialsPlugin, (),
    _(u'Twitter credentials plugin'),
    u'')

authenticatorFactory = AuthenticatorPluginFactory(
    "principal.twitter", AuthenticatorPlugin, ((IUsersPlugin, ''),),
    _(u'Twitter users'),
    u'')
