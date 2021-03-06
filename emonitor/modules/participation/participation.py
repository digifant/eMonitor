from sqlalchemy.orm.collections import attribute_mapped_collection
from emonitor.extensions import db
from emonitor.widget.monitorwidget import MonitorWidget
from emonitor.modules.settings.settings import Settings
from emonitor.modules.persons.persons import Person
from emonitor.modules.alarms.alarm import Alarm
from emonitor.extensions import monitorserver
import datetime
import logging
import traceback

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class Participation(db.Model):
    """Participation class"""
    __tablename__ = 'participation'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.BOOLEAN)
    #first try: 0=no, 1=yes, 2=maybe, 4=no feedback
    #2015-12-26: 3=yes 3min, 6=yes 6min, 9=yes 9min, 0=no, -1=maybe
    participation = db.Column(db.Integer)
    _alarm = db.Column('alarm', db.ForeignKey('alarms.id'))
    alarm = db.relationship("Alarm", collection_class=attribute_mapped_collection('id'))
    #alarm = db.relationship('alarms')

    _person = db.Column('person', db.ForeignKey('persons.id'))
    person = db.relationship("Person", collection_class=attribute_mapped_collection('id'))
    _dept = db.Column('dept', db.ForeignKey('departments.id'))
    dept = db.relationship("Department", collection_class=attribute_mapped_collection('id'))
    #dept = db.relationship("Department", collection_class=attribute_mapped_collection('id'))
    timestamp = db.Column('timestamp', db.DateTime)

    def __init__(self, alarm, person, dept=1, participation=0, active=1, dt=''):
        self.participation = participation
        self.active = active
        self._alarm = alarm
        self._person = person
        self._dept = dept
        if dt == '':
            self.timestamp = datetime.datetime.now()
        else:
            self.timestamp = dt

    def getColor(self):
        """
        Get color of car, default *#ffffff*

        :return: colorcode
        """
        if self.participation == 0:
                return "#ff0000"
        if self.participation == 3:
                return "#00ff00"
        if self.participation == 6:
                return "#ffff00"
        if self.participation == 9:
                return "#ff7d00"
        #no feedback
        return "#a79c9c"

    def __str__(self):
        return "Participation id=%s active=%s participation=%s timestamp=%s person=%s alarm=%s dept=%s" % (self.id, self.active, self.participation, self.timestamp, self._person, self._alarm, self._dept)
        #return "todo implement me!"

    @staticmethod
    def yes3minDetailed(alarmid):
        return Participation.yesXminDetailed(alarmid, 3)
    @staticmethod
    def yes6minDetailed(alarmid):
        return Participation.yesXminDetailed(alarmid, 6)
    @staticmethod
    def yes9minDetailed(alarmid):
        return Participation.yesXminDetailed(alarmid, 9)
    @staticmethod
    def yesXminDetailed(alarmid, min=3):
        gl = Participation.query.filter_by(participation=min).join(Participation.person).join(Participation.alarm).filter (Person.groupLeader==True, Alarm.id==alarmid).count()
        pl = Participation.query.filter_by(participation=min).join(Participation.person).join(Participation.alarm).filter (Person.platoonLeader==True, Alarm.id==alarmid).count()
        asgt = Participation.query.filter_by(participation=min).join(Participation.person).join(Participation.alarm).filter (Person.asgt==True, Alarm.id==alarmid).count()
        normal = Participation.query.filter_by(participation=min).join(Participation.person).join(Participation.alarm).filter (Person.asgt==False, Person.platoonLeader==False, Person.groupLeader==False, Alarm.id==alarmid).count()
        rs = ('%s / %s / %s / %s' % (pl, gl, asgt, normal))
        #logger.debug ("yesXminDetailed x=%s %s" % (min,rs))
        return rs

    @staticmethod
    def yesPersonList(alarmid, min=3):
        try:
            prAll = Participation.query.join(Participation.person).join(Participation.alarm).filter (Alarm.id==alarmid).order_by(Person.platoonLeader.desc(), Person.groupLeader.desc(), Person.asgt.desc())
	    prNew = []
            for p in prAll:
               if p.participation==min:
                   prNew.append (p)

            for p in prAll:
                for p2 in prAll:
                    if p.person.id == p2.person.id and p.timestamp != p2.timestamp:
                        #this should not happen!
                        logger.warn ("cleanup participation info needed (dublette) %s" % p.person.lastname)
                        if p.timestamp > p2.timestamp:
                            try:
                                logger.warn ("remove participation info (dublette) %s %s %s" % (p2.person.lastname, p2.timestamp, p2.participation))
                                prNew.remove (p2)
                            except:
                                pass
                        else:
                            try:
                                logger.warn ("remove participation info (dublette) %s %s %s" % (p.person.lastname, p.timestamp, p.participation))
                                prNew.remove (p)
                            except:
                                pass
                        break
        except Exception as e:
            logger.error(traceback.format_exc())

        #ohne dupletten test
        #pr = Participation.query.filter_by(participation=min).join(Participation.person).join(Participation.alarm).filter (Alarm.id==alarmid).order_by(Person.platoonLeader.desc(), Person.groupLeader.desc(), Person.asgt.desc())

        #hack dupletten test
        pr = prNew

        tsL=[]
        for p in pr:
            ts = ''
            if p.person.platoonLeader == True:
                ts = "ZF "
            elif p.person.groupLeader == True:
                ts = "GF "
            if p.person.asgt == True:
                    ts = ts + "Atemschutz"
            ps = '%s (%s, %s)' % (ts, p.person.lastname, p.person.firstname)
            n = '%s, %s' % (p.person.lastname, p.person.firstname)
            #logger.debug(ps)
            tsL.append( (ts, n))
        return tsL


    @staticmethod
    def yes3min(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=3).count()
    @staticmethod
    def yes6min(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=6).count()
    @staticmethod
    def yes9min(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=9).count()

    @staticmethod
    def no(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=0).count()

    @staticmethod
    def maybe(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=-1).count()
    @staticmethod
    def unknown(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=99).count()

    def getParticipationCountYes3min (self):
        return Participation.query.filter_by(_alarm=int(self._alarm), participation=3).count()
    def getParticipationCountYes6min (self):
        return Participation.query.filter_by(_alarm=int(self._alarm), participation=6).count()
    def getParticipationCountYes9min (self):
        return Participation.query.filter_by(_alarm=int(self._alarm), participation=9).count()

    @staticmethod
    def getParticipation(id=0, alarmid=0, qtelegramId='', params=[]):
        logger.debug ("getParticipation alarmid=%s" %alarmid)
        if id != 0:
            return Participation.query.filter_by(id=int(id)).first()
        elif int(alarmid) != 0:
            return Participation.query.filter_by(_alarm=int(alarmid)).order_by('participation').all()
        elif qtelegramId != '':
            #p = Person.getPerson(qtelegramId=qtelegramId).order_by('participation').all()
            #if p != None:
                #return Participation.query.filter_by(_person=p.id)
                #.filter_by(Person.telegramId=qtelegramId, Person.active=True, Alarm.active=True)
            return Participation.query.join(Participation.person) \
                                      .join(Participation.alarm) \
                                      .filter (Person.telegramId==qtelegramId, Alarm.state==1)
        else:
            if 'onlyactive' in params:
                return Participation.query.filter_by(active=1).order_by('alarm', 'participation').all()
            else:
                return Participation.query.order_by('alarm', 'participation').all()

    @staticmethod
    def autoYes(alarmid=0, params=[]):
        autoYesFilterL = [1,2,4,5,10]
        logger.debug ("autoYes alarmid=%s" %alarmid)

        #cpi = Participation.query.filter_by(_alarm=int(alarmid))
        count = 0;
        allP = Person.getPersons (onlyactive=True)
        for p in allP:
            if p.id in autoYesFilterL:
                #person should get auto yes
                if Participation.query.filter_by(_alarm=int(alarmid), _person=p.id).count() == 0:
                    #no participation info -> auto create yes 3min
                    try:
                        part = Participation (alarm=int(alarmid), person=p.id, participation=3)
                        logger.info("auto participation created for %s,%s: 3min" % (p.lastname, p.firstname))
                        count = count + 1
                        db.session.add(part)
                    except:
                        logger.error (traceback.format_exc())
                        db.session.commit()
                else:
                    #we already have participation info
                    #logger.debug ("participation found for %s" % (p.id))
                    pass
        if count > 0:
            db.session.commit()
            ##signal.send('alarm', 'updated', alarmid=alarm_id)
            #monitorserver.sendMessage('0', 'reset')  # refresh monitor layout
            plist = alarm.plist
            psummary = alarm.psummary
            logger.info ("sending websocket command")
            monitorserver.sendMessage (clientid='0', operation='websocket_participation', command='websocket_participation', detailed=plist )
            monitorserver.sendMessage (clientid='0', operation='websocket_participation_summary', command='websocket_participation_summary', detailed=psummary )
        return count


    @staticmethod
    def getParticipationDict():
        """
        Get dict of participation, id as key

        :return: dict with :py:class:`emonitor.modules.cars.car.Car`
        """
        ret = {}
        for p in Participation.getParticipation():
            ret[p.id] = p
        return ret

    #hack
    @property
    def participationStr (self):
        return Settings.getParticipationTypes()[self.participation]

class ParticipationWidget(MonitorWidget):
    """person participation widget for alarms"""
    template = 'widget.participation.html'
    size = (5, 1)

    def addParameters(self, **kwargs):
        self.params.update(kwargs)

class ParticipationWidgetList(MonitorWidget):
    """person participation list widget for alarms"""
    template = 'widget.participationList.html'
    size = (5, 5)

    def addParameters(self, **kwargs):
        self.params.update(kwargs)
