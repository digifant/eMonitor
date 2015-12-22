from emonitor.utils import Module
from emonitor.extensions import babel
from .content_admin import getAdminContent


class BofhtestModule(Module):
    """
    Definition of users module with admin area
    """
    info = dict(area=['admin'], name='bofhtest', path='bofhtest', icon='fa-user', version='0.1')
    helppath = '/emonitor/modules/bofhtest/help/'
    
    def __repr__(self):
        return "bofhtestmodule"

    def __init__(self, app):
        Module.__init__(self, app)
        # add template path
        app.jinja_loader.searchpath.append("%s/emonitor/modules/bofhtest/templates" % app.config.get('PROJECT_ROOT'))
        
        babel.gettext(u'module.bofhtest')
        babel.gettext(u'admin.bofhtest.title')
        #babel.gettext(u'userlevel.notset')
        #babel.gettext(u'userlevel.admin')
        #babel.gettext(u'userlevel.user')

    def getAdminContent(self, **params):
        """
        Call *getAdminContent* of users class

        :param params: send given parameters to :py:class:`emonitor.modules.bofhtest.content_admin.getAdminContent`
        """
        return getAdminContent(self, **params)
