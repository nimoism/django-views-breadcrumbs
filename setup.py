from setuptools import setup, find_packages

import views_breadcrumbs as meta

def long_description():
    with open('README.rst') as f:
        rst = f.read()
        return rst

setup(
    name='django-views-breadcrumbs',
    version=meta.__version__,
    description=meta.__doc__,
    author=meta.__author__,
    author_email=meta.__contact__,
    long_description=long_description(),
    url='https://github.com/nimoism/django-views-breadcrumbs',
    platforms=["any"],
    packages=find_packages(),
    scripts=[],
    install_requires=[
        'django>=1.3',
        'django-appconf',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Environment :: Web Environment',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Framework :: Django',
    ]

)