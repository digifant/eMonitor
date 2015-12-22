import re
from emonitor.utils import Module
from emonitor.widget.monitorwidget import MonitorWidget
from emonitor.extensions import babel
from emonitor.modules.participation.participation import Participation
from emonitor.modules.participation.content_admin import getAdminContent
from emonitor.modules.participation.content_frontend import getFrontendData
from emonitor.modules.participation.participation import ParticipationWidget


class ParticipationModule(object, Module):
    """
    Definition of participation module with frontend, admin and widget area
    """
    info = dict(area=['admin', 'frontend', 'widget'], name='participation', path='participation', icon='fa-truck', version='0.1')

    def __repr__(self):
        return "participation"

    def __init__(self, app):
        """
        Add specific parameters and configuration to app object

        :param app: flask wsgi application
        """
        Module.__init__(self, app)
        # add template path
        app.jinja_loader.searchpath.append("%s/emonitor/modules/participation/templates" % app.config.get('PROJECT_ROOT'))

        self.widgets = [ParticipationWidget('participation')]

        # create database tables
        from emonitor.modules.participation.participation import Participation
        #classes.add('car', Car)
        #db.create_all()

        # translations
        babel.gettext(u'module.participation')
        babel.gettext(u'participation')

    def updateAdminSubNavigation(self):
        """
        Add submenu entries for admin area
        """
        from emonitor.modules.settings.department import Department
        self.adminsubnavigation = []
        for dep in Department.getDepartments():
            self.adminsubnavigation.append(('/admin/cars/%s' % dep.id, dep.name))

    def getHelp(self, area="frontend", name=""):
        """
        Get special html content for car module

        :param optional area: *frontend*, *admin*
        :param name: name of help template
        """
        name = name.replace('help/', '').replace('/', '.')
        name = re.sub(".\d+", "", name)
        return super(ParticipationModule, self).getHelp(area=area, name=name)

    def getAdminContent(self, **params):
        """
        Call *getAdminContent* of cars class

        :param params: send given parameters to :py:class:`emonitor.modules.cars.content_admin.getAdminContent`
        """
        self.updateAdminSubNavigation()
        return getAdminContent(self, **params)

    def getAdminData(self):
        """
        Call *getAdminData* method of cars class and return values

        :return: return result of method
        """
        return ""

    def getFrontendData(self):
        """
        Call *getFrontendData* of cars class
        """
        return getFrontendData(self)
