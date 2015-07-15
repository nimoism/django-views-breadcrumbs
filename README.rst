==========================================================================
django-views-breadcrumbs - Breadcrumbs support on django class based views
==========================================================================

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

    @breadcrumb(lambda args, kwargs, context, request: context['category'].name, parent='project.views.index')
    class ProductListView(ListView):
        ...

where ``project.views.index`` is view name of parent view.

If you want to pass ``object`` (first) function parameters to parent, you should use ``parent_args``.
When you pass ``parent_args``, parent view will be not dispatched::

    @breadcrumb(lambda args, kwargs, context, request: context['product'].name,
                parent='project.views.product-list',
                parent_args=lambda args, kwargs, context, request: [], {}, {'category': context['product'].category}
               )
    class ProductDetailView(DetailView):
        ...

``parent_args`` must return list of args, kwargs and context, witch will pass to parent breadcrumb ``object`` parameter

Settings
--------

Set ``BREADCRUMBS_TEMPLATE_CONTEXT_NAME`` to change context name (default is ``breadcrumbs``)::

    BREADCRUMBS_TEMPLATE_CONTEXT_NAME = 'breadcrumbs'

Middleware
----------

If you want to get warnings when middle view of breadcrumbs branch is dispatched
(it means dispatched not only current view, but also parent), you can use ``BreadcrumbsWarningMiddleware``::

    MIDDLEWARE_CLASSES += ('views_breadcrumbs.middleware.BreadcrumbsWarningMiddleware', )

