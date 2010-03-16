from zope import interface, schema
from zope.i18nmessageid.message import MessageFactory
from zope.app.authentication.interfaces import IPrincipalInfo


_ = MessageFactory("zojax.authentication.twitter")


class ITwitterAuthenticationProduct(interface.Interface):
    """ product """

    consumerKey = schema.TextLine(title=_(u"Consumer Key"),
                                  description=_(u"You can get this at http://twitter.com/oauth_clients"),
                                  required=True,)

    consumerSecret = schema.TextLine(title=_(u"Consumer Secret"),
                                  description=_(u"You can get this at http://twitter.com/oauth_clients"),
                                  required=True,)


class ITwitterPrincipal(interface.Interface):
    """ twitter principal """

    login = schema.TextLine(
        title=_("Login"),
        description=_("Twitter username of the principal."))

    twitterId = schema.Int(title=_(u"Twitter ID"))
    

class ITwitterPrincipalMarker(interface.Interface):
    """ twitter principal marker """
    

class ITwitterPrincipalInfo(IPrincipalInfo):
    """ principal info """

    internalId = interface.Attribute('Internal ID')

    twitterId = interface.Attribute('Twitter ID')
    

class ITwitterCredentials(interface.Interface):

    requestToken = interface.Attribute(u"requestToken")

    accessToken = interface.Attribute(u"accessToken")


class ITwitterAuthenticator(interface.Interface):

    def getPrincipalByTwitterId():
        """ Return principal id by her twitter ID. Return None if
        principal with given ID does not exist. """
