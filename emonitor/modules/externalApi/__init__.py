from emonitor.utils import Module
from emonitor.extensions import babel
from .content_admin import getAdminContent
from emonitor.extensions import monitorserver
from emonitor.modules.alarms.alarm import Alarm
from emonitor.modules.participation import Participation
from flask import Flask, jsonify, abort, request
import logging
import datetime

logger = logging.getLogger (__name__)
logger.setLevel (logging.DEBUG)


class ExternalapiModule(Module):
    """
    Definition of users module with admin area
    """
    info = dict(area=['admin'], name='externalApi', path='externalApi', icon='fa-user', version='0.1')
    helppath = '/emonitor/modules/externalApi/help/'

    def __repr__(self):
        return "externalApimodule"

    def __init__(self, app):
        Module.__init__(self, app)
        # add template path
        app.jinja_loader.searchpath.append("%s/emonitor/modules/externalApi/templates" % app.config.get('PROJECT_ROOT'))

        babel.gettext(u'module.externalApi')
        babel.gettext(u'admin.externalApi.title')

        #curl -i -X GET http://192.168.1.145:8080/externalApi/rest//client
        @app.route('/externalApi/rest/client', methods=['GET', 'POST'])
        def rest_connected_client_static():
            if request.method == 'GET':
                #logger.debug("REST GET connected clients")
                clientmap = monitorserver.getClients()
                #logger.debug("clientmap %s" % clientmap)
                #clientmap {'1': [None, <Monitor 1L>], '3': [None, <Monitor 3L>], '2': [('192.168.1.176', 's001w7176.sr.sr-intra.de'),
                #<Monitor 2L>], '5': [None, <Monitor 5L>], '4': [None, <Monitor 4L>]}
                #ERROR:cherrypy.error:[14/Oct/2016:11:42:44] ENGINE TypeError('<Monitor 1L> is not JSON serializable',)
                resultmap = {}
                for c in clientmap:
                    if clientmap[c][0] != None:
                        resultmap[c]=clientmap[c][0]
                return jsonify (monitor=resultmap)
            elif request.method == 'POST':
                logger.debug ("REST POST json=%s" % request.json)
                if not request.json or ( not 'clientId' in request.json or not 'command' in request.json ):
                    #curl -i -X POST -H "Content-Type: application/json" http://feuerwehr/participation/rest/participation -d ' { "telegramId" : "007" , "participation":3 } '
                    logger.debug("clientId or command missing!")
                    abort(400)
                try:
                  clientId = int(request.json['clientId'])
                except ValueError:
                  abort(400)
                command = request.json['command']
                logger.debug("/externalApi/rest/client POST clientId=%s command=%s" % (clientId, command))
                if command == 'display_off':
                    #curl -i -XPOST -H "Content-Type: application/json" http://192.168.1.145:8080/externalApi/rest/client -d ' { "clientId" : "0" , "command":"display_off" } '
                    a = Alarm.getAlarms(state=1)
                    if len(a)<1:
                        monitorserver.sendMessage(clientId, 'display_off')  # display off only if no active alarm
                        logger.debug("/externalApi/rest/client POST display_off command for client %s" % clientId)
                        return jsonify({'result': True , 'command':command})
                    else:
                        logger.debug("/externalApi/rest/client POST display_on command for client %s ignored (active alarm!)" % clientId)
                        return jsonify({'result': False , 'command':command, 'message':'ignored -> active alarm!'})
                elif command == 'display_on':
                    #curl -i -XPOST -H "Content-Type: application/json" http://192.168.1.145:8080/externalApi/rest/client -d ' { "clientId" : "0" , "command":"display_on" } '
                    logger.debug("/externalApi/rest/client POST display_on command for client %s" % clientId)
                    monitorserver.sendMessage(clientId, 'display_on')  # display on
                    return jsonify({'result': True , 'command':command})
                elif command =='test':
                    #curl -i -XPOST -H "Content-Type: application/json" http://192.168.1.145:8080/externalApi/rest/client -d ' { "clientId" : "1" , "command":"test" } '
                    logger.debug("/externalApi/rest/client POST test command")
                    return jsonify({'result': True , 'command':command})
                #not implemented
                abort (501)
            abort(404)

        @app.route('/externalApi/rest/alarm', methods=['GET', 'POST'])
        def rest_alarm_static():
            if request.method == 'GET':
                #curl -i -X GET http://192.168.1.145:8080/externalApi/rest//alarm
                logger.debug("REST GET alarm")
                aa = Alarm.getActiveAlarms()
                logger.debug("active alarms %s" % aa)
                resultmap = {}
                for a in aa:
                    resultmap[a.id]=[a.key. a.type, a.state, a.street]
                return jsonify (alarm=resultmap)
            elif request.method == 'POST':
                logger.debug ("REST POST json=%s" % request.json)
                if not request.json or not 'command' in request.json:
                    logger.debug("command missing!")
                    abort(400)
                command = request.json['command']
                logger.debug("/externalApi/rest/alarm POST command=%s" % (command))
                if command == 'close_expired':
                    #curl -i -XPOST -H "Content-Type: application/json" http://192.168.1.145:8080/externalApi/rest/client -d ' { "clientId" : "0" , "command":"display_off" } '
                    al = Alarm.closeAllExpiredActiveAlarms()
                    logger.debug("/externalApi/rest/alarm POST close_expired")
                    return jsonify({'result': True , 'command':command, 'close_list': al})
                elif command =='test':
                    #curl -i -XPOST -H "Content-Type: application/json" http://192.168.1.145:8080/externalApi/rest/alarm -d ' { "clientId" : "1" , "command":"test" } '
                    logger.debug("/externalApi/rest/alarm POST test command")
                    return jsonify({'result': True , 'command':command})
                #not implemented
                abort (501)
            abort(404)

        @app.route('/externalApi/rest/participation', methods=['POST'])
        def rest_eapi_participation_static():
            if request.method == 'POST':
                logger.debug ("REST POST json=%s" % request.json)
                if not request.json or not 'command' in request.json:
                    logger.debug("command missing!")
                    abort(400)
                command = request.json['command']
                logger.debug("/externalApi/rest/participation POST command=%s" % (command))
                if command == 'auto_yes':
                    #curl -i -XPOST -H "Content-Type: application/json" http://192.168.1.145:8080/externalApi/rest/participation -d ' { "command":"auto_yes" } '
                    #find active alarm
                    al = Alarm.getAlarms(state=1)
                    for a in al:
                        logger.debug("alarm %s" % a)
                    try:
                        alarm = al[0]
                    except IndexError:
                        logger.error ("no active alarm found -> create one first!")
                        abort(400)
                    count = Participation.autoYes(alarmid=alarm.id)
                    logger.info ("rest_participation_static() called participation::autoYes for alarmid=%s ; created %s auto yes 3min" % (alarm.id,count))
                    return jsonify({'result': True , 'command':command, 'count':count})

    def getAdminContent(self, **params):
        """
        Call *getAdminContent* of users class

        :param params: send given parameters to :py:class:`emonitor.modules.externalApi.content_admin.getAdminContent`
        """
        return getAdminContent(self, **params)
