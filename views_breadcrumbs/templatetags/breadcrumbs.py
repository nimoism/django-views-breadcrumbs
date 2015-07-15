from django.conf import settings

__author__ = 'Dmitry Puhov (dmitry.puhov@gmail.com)'

from django import template


register = template.Library()


@register.inclusion_tag("breadcrumbs/breadcrumbs.html")
def breadcrumbs(breadcrumbs_):
    return {settings.BREADCRUMBS_TEMPLATE_CONTEXT_NAME: breadcrumbs_}
