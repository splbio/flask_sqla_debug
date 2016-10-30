from distutils.core import setup
setup(
  name = 'flask_sqla_debug',
  packages = ['flask_sqla_debug'], # this must be the same as the name above
  version = '0.1',
  description = 'Helpers for debugging flask and sqlalchemy performance',
  author = 'Alfred Perlstein',
  author_email = 'alfred.perlstein@gmail.com',
  url = 'https://github.com/splbio/flask_sqla_debug', # use the URL to the github repo
  download_url = 'https://github.com/splbio/flask_sqla_debug/tarball/0.1', # I'll explain this in a second
  keywords = ['testing', 'logging', 'debug', 'flask', 'sqlalchemy'], # arbitrary keywords
  classifiers = [],
)
