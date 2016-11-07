from distutils.core import setup

setup(
    name = 'afg',
    packages = ['afg'],
    version = '0.1',
    description = 'Alexa Flask Guide for Flask-ASK',
    author = 'Anton Dort-Golts',
    author_email = 'dortgolts@gmail.com',
    url = 'https://github.com/peterldowns/mypackage',
    download_url = 'https://github.com/peterldowns/mypackage/tarball/0.1',
    keywords = ['alexa', 'flask-ask', 'fsm'],
    install_requires=[
        'flask-ask',
        'PyYAML',
        'Fysom',
        'wrapt'
    ],
    classifiers = [],
)
