from zope import interface
from zojax.principal.twitter.interfaces import \
    ITwitterAuthenticationProduct
from zojax.product.product import Product


class TwitterAuthenticationProduct(Product):
    interface.implements(ITwitterAuthenticationProduct)

    def install(self):
        super(TwitterAuthenticationProduct, self).install()
        self.update()

    def update(self):
        pass
