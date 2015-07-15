==============================================================
django-views-breadcrumbs - Breadcrumbs support on django views
==============================================================

Using django-views-breadcrumbs
==============================

To enable ``django-views-breadcrumbs`` you need add ``views_breadcrumbs`` to ``INSTALLED_APPS``::

    INSTALLED_APPS += ('views_breadcrumbs',)

To add breadcrumb to view, use ``breadcrumb`` decorator::

    from views_breadcrumbs.views import breadcrumb
    ...
    @breadcrumb('index')
    class IndexView(View):
        ...

For most complex use::

    @breadcrumb(lambda args, kwargs, context, request: context['object'].name, parent='project.views.index')
    class ObjectDetail(DetailView):
        ...

where ``project.views.index`` is view name of parent view.

Settings
--------

Set ``BREADCRUMBS_TEMPLATE_CONTEXT_NAME`` to change context name (default is ``breadcrumbs``)::

    BREADCRUMBS_TEMPLATE_CONTEXT_NAME = 'breadcrumbs'
