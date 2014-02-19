from setuptools import setup, find_packages
import os


version = '0.1dev'

setup(name='zojax.principal.twitter',
      version=version,
      description="Twitter authentication plugin for zojax based on OAuth",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          "Programming Language :: Python",
      ],
      keywords='',
      author='Andrey Fedoseev',
      author_email='andrey.fedoseev@gmail.com',
      url='',
      license='',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['zojax', 'zojax.principal'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
            'setuptools',
            'simplejson',
            'oauth',
            'python-twitter',
            'zojax.product',
            'zojax.content.type',
            'zojax.authentication',
            'zojax.principal.users',
            'zojax.principal.field',
            'zojax.cache',
            'zojax.portlet',

          # -*- Extra requirements: -*-
      ],
      extras_require=dict(test=['zope.app.testing', ]
      ),
      entry_points="""
      # -*- Entry points: -*-
      """,
      dependency_links=['http://download.zope.org/distribution', 'http://eggs.carduner.net/'],
)
