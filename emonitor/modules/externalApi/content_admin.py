from flask import request, render_template, current_app
from emonitor.extensions import db
from emonitor.extensions import babel

def getAdminContent(self, **params):
    """
    Deliver admin content of module user

    :param params: use given parameters of request
    :return: rendered template as string
    """


    #params.update({'externalApi': 'hello module', 'test2':babel.gettext(u'admin.externalApi.title') })
    return render_template('admin.externalApi.html', **params)
