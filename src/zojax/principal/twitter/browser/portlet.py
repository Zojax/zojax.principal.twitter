from zope import component
from zope.app.security.interfaces import IUnauthenticatedPrincipal

from zojax.controlpanel.interfaces import IConfiglet
from zojax.portlet.portlet import PortletBase


class TwitterSignIn(PortletBase):

    def isAvailable(self):
        if not IUnauthenticatedPrincipal.providedBy(self.request.principal):
            return False
        configlet = component.getUtility(IConfiglet, name="product.zojax-authentication-twitter")
        if not configlet.consumerKey or not configlet.consumerSecret:
            return False
        return True
