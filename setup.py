from distutils.core import setup

setup(
    name = 'afg',
    packages = ['afg'],
    version = '0.1.1',
    description = 'Alexa Flask Guide for Flask-ASK',
    author = 'Anton Dort-Golts',
    author_email = 'dortgolts@gmail.com',
    url = 'https://github.com/dgtony/afg',
    download_url = 'https://github.com/dgtony/afg/tarball/0.1.1',
    keywords = ['alexa', 'flask-ask', 'fsm'],
    install_requires=[
        'flask-ask',
        'PyYAML',
        'Fysom',
        'wrapt'
    ],
    classifiers = [],
)
