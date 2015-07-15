__author__ = 'Dmitry Puhov (dmitry.puhov@gmail.com)'

from appconf import AppConf


class ViewBreadcrumbsConf(AppConf):
    TEMPLATE_CONTEXT_NAME = 'breadcrumbs'

    class Meta(object):
        prefix = 'BREADCRUMBS'
