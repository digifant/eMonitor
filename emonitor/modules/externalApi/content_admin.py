from flask import request, render_template, current_app
from emonitor.extensions import db
from emonitor.extensions import babel
from emonitor.modules.alarms.alarm import Alarm
from emonitor.extensions import monitorserver
from flask import Flask, jsonify, abort, request
import logging

logger = logging.getLogger (__name__)
logger.setLevel (logging.DEBUG)


def getAdminContent(self, **params):
    """
    Deliver admin content of module user

    :param params: use given parameters of request
    :return: rendered template as string
    """
    
    if request.method == 'POST':
        logger.debug("getAdminContent %s" % request.form.get('action') )
        if request.form.get('action') == 'monitor_off':            
            monitorserver.sendMessage('0', 'display_off')
            params.update ({'mesg':'triggered display OFF'})
        elif request.form.get('action') == 'monitor_on':
            monitorserver.sendMessage('0', 'display_on')
            params.update ({'mesg':'triggered display ON'})
        elif request.form.get('action') == 'close_expired_alarms':
            Alarm.closeAllExpiredActiveAlarms()
            params.update ({'mesg':'triggered close expired alarms'})


    #params.update({'externalApi': 'hello module', 'test2':babel.gettext(u'admin.externalApi.title') })
    return render_template('admin.externalApi.html', **params)
