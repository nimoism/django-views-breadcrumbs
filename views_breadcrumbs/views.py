from django.utils.encoding import force_text
import six

__author__ = 'Dmitry Puhov (dmitry.puhov@gmail.com)'

# -*- coding=utf-8 -*-

import inspect
from functools import wraps
from django.core.urlresolvers import reverse, resolve, NoReverseMatch
from django.http.response import HttpResponseRedirectBase, HttpResponseNotAllowed
from django.utils.http import urlquote
import types


class Breadcrumbs(list):
    VIEW_CONTEXT_NAME = 'breadcrumbs'


class Breadcrumb(object):

    def __init__(self, object_, view=None, view_args=None, view_kwargs=None, query_string=''):
        if view_args is None:
            view_args = []
        if view_kwargs is None:
            view_kwargs = {}
        self.obj = object_
        self.view = view
        if self.view and hasattr(self.view, '__call__'):
            view_name = "%s.%s" % (self.view.__module__, self.view.__name__)
        elif isinstance(self.view, basestring):
            view_name = self.view
        else:
            view_name = None
        if view_name:
            url = reverse(view_name, args=view_args, kwargs=view_kwargs)
            if query_string:
                url += '?' + query_string
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
    PARENT_VIEW_NAME_KWARG = 'bc_view_name'
    PARENT_CONTEXT_KWARG = 'bc_context'
    REQUEST_DISPATCHED = 'bc_dispatched'

    def __init__(self, obj=None, parent=None, parent_args=None, get_params=None, static_object=None):
        self.object = obj
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

            view_name = kwargs.pop(self.PARENT_VIEW_NAME_KWARG, None)
            first_breadcrumb = view_name is None
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
            query_string = self.get_query_string(args, kwargs, context, request)

            objects = object_ if isinstance(object_, types.ListType) else [object_]
            for object_ in reversed(objects):
                if object_ is not None:
                    breadcrumbs.insert(0, Breadcrumb(object_, view_name, view_args=args, view_kwargs=kwargs,
                                                     query_string=query_string))
            parent_response = self.dispatch_parent(breadcrumbs, request, args, kwargs, context)
            if hasattr(response, 'context_data'):
                if response.context_data is None:
                    response.context_data = {}
                response.context_data[Breadcrumbs.VIEW_CONTEXT_NAME] = breadcrumbs
            response.dispatched_views.extend(parent_response.dispatched_views)
            return response

        return _dispatch

    def get_parent_view_name(self, request, args, kwargs, context):
        if hasattr(self.parent, '__call__'):
            parent = self.parent(args, kwargs, context, request)
        else:
            parent = self.parent
        return parent

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
        p_view_name = self.get_parent_view_name(request, args, kwargs, context)
        response = self.dispatch_parent_by_view_name(breadcrumbs, p_view_name, request, args, kwargs, context)
        if not response.is_dispatched:
            response = self.dispatch_parent_by_func_name(breadcrumbs, p_view_name)
        if not response.is_dispatched:
            p_args, p_kwargs, p_context = self.get_parent_args(request, args, kwargs, context)
            raise RuntimeError("Parent not dispatched %s, args:%s, kwargs:%s" % (p_view_name, p_args, p_kwargs))
        return response

    def dispatch_parent_by_view_name(self, breadcrumbs, parent_view_name, request, args, kwargs, context):
        """
        @param breadcrumbs: breadcrumbs
        @type breadcrumbs: Breadcrumbs
        @param parent_view_name: parent view name
        @type parent_view_name: str
        @param request: http request
        @type request: django.http.request.HttpRequest
        @param args: parent args
        @type args: list
        @param kwargs: parent kwargs
        @type kwargs: dict
        @param context: parent context
        @type context: dict
        @return: response
        @rtype: django.http.http.HttpResponse|FakeResponse
        """
        p_args, p_kwargs, p_context = self.get_parent_args(request, args, kwargs, context)
        try:
            url = reverse(parent_view_name, args=p_args, kwargs=p_kwargs)
        except NoReverseMatch as e:
            response = FakeResponse()
        else:
            func = resolve(url).func
            m = __import__(func.__module__, globals(), locals(), [func.__name__, ])
            parent = getattr(m, func.__name__)
            p_kwargs[self.PARENT_VIEW_NAME_KWARG] = parent_view_name
            p_kwargs[self.PARENT_CONTEXT_KWARG] = p_context
            if isinstance(parent, types.TypeType):
                response = parent(request=request, kwargs=p_kwargs).dispatch(request, *p_args, **p_kwargs)
                response.is_dispatched = True
            elif isinstance(parent, types.FunctionType):
                response = self.insert_old_style_breadcrumbs_bc(breadcrumbs, parent)
            else:
                raise RuntimeError("Wrong parent type: %s" % type(parent))
            if hasattr(response, 'context_data'):
                for bc in reversed(list(response.context_data[Breadcrumbs.VIEW_CONTEXT_NAME])):
                    breadcrumbs.insert(0, bc)
        finally:
            p_kwargs.pop(self.PARENT_VIEW_NAME_KWARG, None)
            p_kwargs.pop(self.PARENT_CONTEXT_KWARG, None)
        return response

    @classmethod
    def insert_old_style_breadcrumbs_bc(cls, breadcrumbs, parent_func):
        """
        @param breadcrumbs: breadcrumbs
        @type breadcrumbs: Breadcrumbs
        @param parent_func: function
        @type parent_func: function
        @return: is inserted
        @rtype: bool
        """
        if hasattr(parent_func, 'bc_obj'):
            p_obj = parent_func.bc_obj
            p_view_args = []
            p_view_kwargs = {}
            breadcrumbs.insert(0, Breadcrumb(p_obj, parent_func, p_view_args, p_view_kwargs))
            return FakeResponse()
        return FakeResponse(is_dispatched=False)

    def dispatch_parent_by_func_name(self, breadcrumbs, parent_full_func_name):
        """
        @param breadcrumbs: breadcrumbs
        @type breadcrumbs: Breadcrumbs
        @param parent_full_func_name: full function name with module
        @type parent_full_func_name: str
        @return: is dispatched
        @rtype: bool
        """
        try:
            module_name, func_name = parent_full_func_name.rsplit('.', 1)
            module = __import__(module_name, globals(), locals(), [func_name])
            p_view_func = getattr(module, func_name)
            response = self.insert_old_style_breadcrumbs_bc(breadcrumbs, p_view_func)
        except (ImportError, AttributeError, ValueError) as e:
            response = FakeResponse()
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
