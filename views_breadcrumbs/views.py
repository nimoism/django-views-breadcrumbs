# -*- coding=utf-8 -*-
from __future__ import unicode_literals

from django.utils.encoding import force_text
import six
import inspect
from functools import wraps
from django.core.urlresolvers import reverse, resolve, NoReverseMatch, get_resolver
from django.http.response import HttpResponseRedirectBase, HttpResponseNotAllowed
from django.utils.http import urlquote
import types


__author__ = 'Dmitry Puhov (dmitry.puhov@gmail.com)'


class Breadcrumbs(list):
    VIEW_CONTEXT_NAME = 'breadcrumbs'


class Breadcrumb(object):

    def __init__(self, object_, url=None):
        self.obj = object_
        self.url = url

    def __str__(self):
        result = self.__unicode__()
        if six.PY2:
            return result.encode('utf-8')
        return result

    def __unicode__(self):
        return force_text(self.obj)


class FakeResponse(object):
    def __init__(self, context=None, is_dispatched=True):
        if context is None:
            context = {}
        self.context_data = context
        self.is_dispatched = is_dispatched
        self.view_dispatch_count = 0
        self.dispatched_views = []


class BreadcrumbDecorator(object):
    PARENT_VIEW = 'bc_view'
    PARENT_CONTEXT_KWARG = 'bc_context'
    REQUEST_DISPATCHED = 'bc_dispatched'

    def __init__(self, obj=None, view_name=None, parent=None, parent_args=None, get_params=None, static_object=None):
        self.object = obj
        self.view_name = view_name
        self.parent = parent
        if parent_args is None:
            parent_args = ([], {}, {})
        self.parent_args = parent_args
        if get_params is None:
            get_params = []
        self.get_params = get_params
        self.view = None
        if static_object is None:
            static_object = False
        self.is_static_object = static_object

    def __call__(self, view, *args, **kwargs):
        self.view = view
        if isinstance(view, types.TypeType):
            view.dispatch = self.dispatch(view.dispatch)
            return view
        elif isinstance(view, types.FunctionType):
            return self.dispatch(view)
        else:
            raise RuntimeError("Wrong decorated %s" % view)

    def dispatch(self, dispatch):

        @wraps(dispatch)
        def _dispatch(*args, **kwargs):
            if inspect.ismethod(dispatch):
                request = args[1]
                cut_args_length = 2
            elif inspect.isfunction(dispatch):
                request = args[0]
                cut_args_length = 1
            else:
                raise RuntimeError("Wrong dispatch type: %s" % type(dispatch))

            view_name, view = kwargs.pop(self.PARENT_VIEW, (None, None))
            first_breadcrumb = view_name is None
            if self.view_name:
                view_name = self.view_name
            if view_name is None:
                view_name = resolve(request.path).url_name
            context = kwargs.pop(self.PARENT_CONTEXT_KWARG, None)
            response = None
            if not first_breadcrumb:
                if context:
                    response = FakeResponse(context)

                if not hasattr(self.object, '__call__'):
                    response = FakeResponse()

                if hasattr(self.is_static_object, '__call__'):
                    static_object_context = context if context else {}
                    is_static_object = self.is_static_object(args, kwargs, static_object_context, request)
                else:
                    is_static_object = self.is_static_object
                if is_static_object:
                    response = FakeResponse(context)

            if not response:
                response = dispatch(*args, **kwargs)
                response.view_dispatch_count = 1
                setattr(request, self.REQUEST_DISPATCHED, True)
                if not hasattr(response, 'dispatched_views'):
                    response.dispatched_views = []
                if isinstance(response, (HttpResponseRedirectBase, HttpResponseNotAllowed)) \
                        or request.method.upper() in ('OPTIONS', ):
                    return response
                response.dispatched_views.append(self.view)
                if hasattr(response, 'context_data'):
                    context = response.context_data
            object_ = self.object(args, kwargs, context, request) if hasattr(self.object, '__call__') else self.object
            args = args[cut_args_length:]

            breadcrumbs = Breadcrumbs()
            if first_breadcrumb:
                url = request.get_full_path()
            else:
                query_string = self.get_query_string(args, kwargs, context, request)
                url = reverse(view_name, args=args, kwargs=kwargs)
                if query_string:
                    url += '?' + query_string

            objects = object_ if isinstance(object_, types.ListType) else [object_]
            for object_ in reversed(objects):
                if object_ is not None:
                    breadcrumbs.insert(0, Breadcrumb(object_, url))
            parent_response = self.dispatch_parent(breadcrumbs, request, args, kwargs, context)
            if hasattr(response, 'context_data'):
                if response.context_data is None:
                    response.context_data = {}
                response.context_data[Breadcrumbs.VIEW_CONTEXT_NAME] = breadcrumbs
            response.dispatched_views.extend(parent_response.dispatched_views)
            return response

        return _dispatch

    def get_parent_view(self, request, args, kwargs, context):
        if hasattr(self.parent, '__call__'):
            parent = self.parent(args, kwargs, context, request)
        else:
            parent = self.parent
        if isinstance(parent, (types.ListType, types.TupleType)):
            parent_view_name, parent_view = self.parent
        elif isinstance(parent, types.StringTypes):
            p_args, p_kwargs, p_context = self.get_parent_args(request, args, kwargs, context)
            url = reverse(parent, args=p_args, kwargs=p_kwargs)
            parent_view_name, parent_view = parent, resolve(url).func
        else:
            raise AttributeError('Wrong parent attribute')
        return parent_view_name, parent_view

    def get_parent_args(self, request, args, kwargs, context):
        parent_args = None
        if hasattr(self.parent_args, '__call__'):
            parent_args = self.parent_args(args, kwargs, context, request)
        if parent_args is None:
            parent_args = ([], {}, {})
        p_args, p_kwargs, p_context = parent_args
        return p_args, p_kwargs, p_context

    def dispatch_parent(self, breadcrumbs, request, args, kwargs, context):
        if not self.parent:
            return FakeResponse()
        parent_view_name, parent_view = self.get_parent_view(request, args, kwargs, context)
        p_args, p_kwargs, p_context = self.get_parent_args(request, args, kwargs, context)

        p_kwargs[self.PARENT_VIEW] = (parent_view_name, parent_view)
        p_kwargs[self.PARENT_CONTEXT_KWARG] = p_context
        response = parent_view(request, *p_args, **p_kwargs)
        p_kwargs.pop(self.PARENT_VIEW, None)
        p_kwargs.pop(self.PARENT_CONTEXT_KWARG, None)

        response.is_dispatched = True
        if hasattr(response, 'context_data'):
            for bc in reversed(list(response.context_data[Breadcrumbs.VIEW_CONTEXT_NAME])):
                breadcrumbs.insert(0, bc)
        if not response.is_dispatched:
            p_args, p_kwargs, p_context = self.get_parent_args(request, args, kwargs, context)
            raise RuntimeError("Parent not dispatched %s, args:%s, kwargs:%s" %
                               (parent_view_name, p_args, p_kwargs))
        return response

    def get_query_string(self, args, kwargs, context, request):
        if hasattr(self.get_params, '__call__'):
            setted_get_params = set(self.get_params(args, kwargs, context, request))
        else:
            setted_get_params = set(self.get_params)
        if '*' in setted_get_params:
            get_params = set(request.GET.keys())
            setted_get_params ^= {'*'}
            get_params |= setted_get_params
        else:
            get_params = setted_get_params
        get_param_pairs = []
        for k, value_list in request.GET.lists():
            if k not in get_params:
                continue
            if '-%s' % k in get_params:
                continue
            get_param_pairs.extend(['%s=%s' % (k, urlquote(v)) for v in value_list if v != ''])
        query_string = '&'.join(get_param_pairs)
        return query_string


breadcrumb = BreadcrumbDecorator
