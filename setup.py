from setuptools import setup, find_packages

import views_breadcrumbs as meta

setup(
    name='django-views-breadcrumbs',
    version=meta.__version__,
    description=meta.__doc__,
    author=meta.__author__,
    author_email=meta.__contact__,
    platforms=["any"],
    packages=find_packages(),
    scripts=[],
    install_requires=[
        'django>=1.3',
        'django-appconf',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ]

)