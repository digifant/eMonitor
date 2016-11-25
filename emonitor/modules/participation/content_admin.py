from flask import request, render_template
from emonitor.extensions import db, signal
from emonitor.modules.settings.department import Department
from emonitor.modules.settings.settings import Settings
from emonitor.modules.participation.participation import Participation
from emonitor.modules.persons.persons import Person
from emonitor.modules.alarms.alarm import Alarm
from emonitor.modules.monitors.monitor import Monitor
from emonitor.modules.monitors.monitorlayout import MonitorLayout
from emonitor.extensions import monitorserver
import datetime
import logging

logger = logging.getLogger (__name__)

def getAdminContent(self, **params):
    """
    Deliver admin content of module cars

    :param params: use given parameters of request
    :return: rendered template as string
    """
    module = request.view_args['module'].split('/')

    #logger.debug( 'participationtypes %s' % Settings.getParticipationTypes()[99])

    if len(module) < 2:
        module.append(u'1')

    if request.method == 'POST':
        if request.form.get('action') == 'createparticipation':  # add
            # todo: settings Settings.getParticipationTypes()
            params.update({'participation': Participation(alarm='',person='',dept=''), 'persons':Person.getPersons(), 'departments': Department.getDepartments(), 'participationtypes': Settings.getParticipationTypes(), 'alarms':Alarm.getAlarms(state=1)})
            return render_template('admin.participation_edit.html', **params)

        elif request.form.get('action') == 'updateparticipation':  # save
            if request.form.get('participation_id') != 'None':  # update
                p = Participation.getParticipation(id=request.form.get('participation_id'))

            else:  # add
                p = Participation(alarm='',person='',dept='')
                db.session.add(p)

            if request.form.get('edit_active') == '1':
                p.active = True
            else:
                p.active = False
            p.participation = request.form.get('edit_participation')
            p._alarm = request.form.get('edit_alarm')
            p._person = request.form.get('edit_person')
            p._dept = request.form.get('edit_department')
            #p.datetime = request.form.get('edit_datetime')
            p.timestamp = datetime.datetime.now()
            db.session.commit()
            signal.send('alarm', 'updated', alarmid=p._alarm)
            #feed new participation as json data to clients (websocket) for smart display update (avoid reloading of the whole site)
            try:
                al = Alarm.getAlarms(state=1)
                try:
                    alarm = al[0]
                except IndexError:
                    logger.error ("no active alarm found -> create one first!")
                    abort(400)
                    plist = alarm.plist
                    monitorserver.sendMessage ('0', 'websocket_participation', {'command':'websocket_participation', 'detailed':plist})
            except Exception as e:
                logger.warn (traceback.format_exc(e))
            monitorserver.sendMessage('0', 'reset')  # refresh monitor layout

        elif request.form.get('action') == 'cancel':
            pass

        elif request.form.get('action').startswith('editparticipation_'):  # edit
            params.update({'participation': Participation.getParticipation(id=request.form.get('action').split('_')[-1]), 'persons':Person.getPersons(), 'departments': Department.getDepartments(), 'participationtypes': Settings.getParticipationTypes(), 'alarms':Alarm.getAlarms(state=1)})
            return render_template('admin.participation_edit.html', **params)

        elif request.form.get('action').startswith('deleteparticipation_'):  # delete
            alarm_id = Participation.getParticipation(id=request.form.get('action').split('_')[-1])._alarm
            db.session.delete(Participation.getParticipation(id=request.form.get('action').split('_')[-1]))
            db.session.commit()
            signal.send('alarm', 'updated', alarmid=alarm_id)
            monitorserver.sendMessage('0', 'reset')  # refresh monitor layout
    try:
        #module[1]
        p = Participation.getParticipation()
    except AttributeError:
        p = []
    params.update({'participation': p})
    return render_template('admin.participation.html', **params)
