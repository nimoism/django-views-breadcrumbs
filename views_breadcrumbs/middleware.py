from logging import getLogger

__author__ = 'Dmitry Puhov (dmitry.puhov@gmail.com)'


logger = getLogger(__name__)

class BreadcrumbsWarningMiddleware(object):

    def process_response(self, request, response):
        if hasattr(response, 'dispatched_views') and len(response.dispatched_views) > 1:
            logger.warning("Breadcrumbs call view dispatch count too much: %s" % len(response.dispatched_views),
                           extra={
                               'request': request,
                               'views': response.dispatched_views,
                           })
        return response
