import os
import pkgutil
import importlib
from flask import render_template, current_app
from emonitor.extensions import classes, babel
from emonitor.utils import Module

from flask import Blueprint

modules = Blueprint('modules', __name__, template_folder="web/templates")


class StartModule(Module):
    """
        startpage for admin area
    """
    info = dict(area=['admin', 'frontend'], name='startpages', path='', version='0.1')
    
    def __repr__(self):
        return "startpages"

    def __init__(self, app):
        Module.__init__(self, app)
        
        babel.gettext(u'module.startpages')

    def frontendContent(self):
        return 0

    def getAdminContent(self, **params):
        return render_template('admin_start.html', **params)
        
    def getFrontendContent(self, **params):
        if 'area' in params:
            defaultarea = dict()
            defaultarea['center'] = classes.get('settings').getFrontendSettings('center')
            defaultarea['west'] = classes.get('settings').getFrontendSettings('west')
            defaultarea['east'] = classes.get('settings').getFrontendSettings('east')

            # load module data
            if defaultarea[params['area']]['module'] == 'default':
                return render_template('frontend.default.html')
            elif defaultarea[params['area']]['module'] in current_app.blueprints['frontend'].modules:
                return current_app.blueprints['frontend'].modules[defaultarea[params['area']]['module']].getFrontendContent(**params)
            else:
                current_app.logger.error("module %s not found for frontend area %s" % (defaultarea[params['area']]['module'], params['area']))
                return ""

        return ""

    def getFrontendData(self, params={}):
        return ""


def init_app(app):

    _count = 0
    #startpage
    m = StartModule(app)
    for area in m.info['area']:
        if area in app.blueprints:
            app.blueprints[area].addModule(m)
    
    for _, name, _ in pkgutil.iter_modules([os.path.join(app.config.get('PROJECT_ROOT'), 'emonitor/modules')]):
        m = importlib.import_module('emonitor.modules.%s' % name, '%sModule' % str(name).title())
        m = eval('m.%sModule' % str(name).title())(app)
        if m.info:
            if 'area' in m.info:
                for area in m.info['area']:
                    if area in app.blueprints:
                        app.blueprints[area].addModule(m)

            if 'messages' in m.info:
                for t in m.info['messages']:
                    app.flashtypes.append('%s.%s' % (name, t))

        _count += 1
    #app.logger.info('modules: %s modules loaded' % _count)

modules.init_app = init_app