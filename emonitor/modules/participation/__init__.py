import re
import traceback
from emonitor.utils import Module
from emonitor.widget.monitorwidget import MonitorWidget
from emonitor.extensions import babel, db
from emonitor.modules.participation.participation import Participation
from emonitor.modules.participation.content_admin import getAdminContent
from emonitor.modules.participation.content_frontend import getFrontendData
from emonitor.modules.participation.participation import ParticipationWidget
from emonitor.modules.participation.participation import ParticipationWidgetList
from emonitor.modules.persons.persons import Person
from emonitor.modules.alarms.alarm import Alarm
from emonitor.extensions import monitorserver
from flask import Flask, jsonify, abort, request
import logging
import datetime
import json

logger = logging.getLogger (__name__)
logger.setLevel (logging.DEBUG)

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

        self.widgets = [ParticipationWidget('participation'), ParticipationWidgetList('participationList')]

        # create database tables
        from emonitor.modules.participation.participation import Participation
        #classes.add('car', Car)
        #db.create_all()

        # translations
        babel.gettext(u'module.participation')
        babel.gettext(u'participation')

        #curl -i -X POST -H "Content-Type: application/json" http://feuerwehr/participation/rest/participation -d ' { "telegramId" : "007" , "participation":3 } '
        @app.route('/participation/rest/participation', methods=['GET', 'POST'])
        def rest_participation_static():
            if request.method == 'GET':
                pl = Participation.getParticipation()
                logger.debug("REST %s" % pl)
                #logger.debug("REST")
                ml=[]
                for p in pl:
                    m={}
                    m['id']=p.id
                    m['timestamp']=p.timestamp
                    m['alarm']=p._alarm
                    m['person']=p._person
                    m['dept']=p._person
                    m['participation']=p.participation
                    ml.append(m)
                return jsonify (participation=ml, test='TEST')
            elif request.method == 'POST':
                logger.debug ("REST POST json=%s" % request.json)
                if not request.json or ( not 'telegramId' in request.json or not 'participation' in request.json ):
                    logger.debug("aha")
                    abort(400)
                person = Person.getPersons(qtelegramId=request.json['telegramId'])
                if person == None:
                    logger.warn ("no person found with telegramId %s" % request.json['telegramId'])
                    abort(400)
                logger.debug("person with telegramId %s found: %s, %s" % (request.json['telegramId'], person.lastname, person.firstname))
                part = Participation.getParticipation(qtelegramId=request.json['telegramId'])
                if part.count()>0:
                    #update
                    for p in part:
                        logger.info("active participation: %s updated to %s" % (p,request.json['participation']))
                        p.participation = request.json['participation']
                        p.timestamp = datetime.datetime.now()
                        db.session.commit()
                else:
                    #create new
                    #find active alarm
                    al = Alarm.getAlarms(state=1)
                    for a in al:
                        logger.debug("alarm %s" % a)
                    try:
                        alarm = al[0]
                    except IndexError:
                        logger.error ("no active alarm found -> create one first!")
                        abort(400)
                    p = Participation (alarm=alarm.id, person=person.id, participation=request.json['participation'])
                    logger.info("new participation created for %s,%s: %s" % (person.lastname, person.firstname, request.json['participation']))
                    db.session.add(p)
                    db.session.commit()
                #signal.send('alarm', 'updated', alarmid=alarm_id)

                #feed new participation as json data to clients (websocket) for smart display update (avoid reloading of the whole site)
                try:
                    al = Alarm.getAlarms(state=1)
                    try:
                        alarm = al[0]
                    except IndexError:
                        logger.error ("no active alarm found -> create one first!")
                        abort(400)
                    plist = alarm.plist
                    logger.info ("sending websocket command")
                    monitorserver.sendMessage (clientid='0', operation='websocket_participation', command='websocket_participation', detailed=plist )
                except Exception as e:
                    logger.warn (traceback.format_exc(e))
                #this would trigger a reload of the whole html site -> unnecessary; we had javascript update of the table
                #monitorserver.sendMessage('0', 'reset')  # refresh monitor layout
                return jsonify({'result': True})
            abort(404)

        #curl -i -X POST -H "Content-Type: application/json" http://emonitor:8080/participation/rest/persons -d ' { "alarmId" : 14 } '
        @app.route('/participation/rest/persons', methods=['POST'])
        def rest_participation_person_static():
                if request.method == 'POST':
                    alarmId = 0
                    if not request.json or ( not 'alarmId' in request.json ):
                        logger.debug("alarmId missing!")
                        abort(400)
                    try:
                        alarmId = int(request.json['alarmId'])
                    except ValueError:
                        logger.debug (traceback.format_exc())
                        abort(400)
                    pl = []
                    try:
                        pl3 = Participation.yesPersonList(alarmid=alarmId)
                        pl6 = Participation.yesPersonList(alarmid=alarmId, min=6)
                        pl9 = Participation.yesPersonList(alarmid=alarmId, min=9)
                        pl0 = Participation.yesPersonList(alarmid=alarmId, min=0)
                    except:
                        logger.error (traceback.format_exc())
                    logger.debug("%s" % pl)
                    #logger.debug("REST")
                    return jsonify (participation3=pl3, participation6=pl6, participation9=pl9, participation0=pl0)
                else:
                    #not implemented
                    abort (501)


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
