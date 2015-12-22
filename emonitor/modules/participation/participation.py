from sqlalchemy.orm.collections import attribute_mapped_collection
from emonitor.extensions import db
from emonitor.widget.monitorwidget import MonitorWidget
from emonitor.modules.settings.settings import Settings
import datetime
import logging

logger = logging.getLogger()

class Participation(db.Model):
    """Car class"""
    __tablename__ = 'participation'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.BOOLEAN)
    #0=no, 1=yes, 2=maybe, 4=no feedback
    participation = db.Column(db.Integer)
    _alarm = db.Column('alarm', db.ForeignKey('alarms.id'))
    _person = db.Column('person', db.ForeignKey('persons.id'))
    _dept = db.Column('dept', db.ForeignKey('departments.id'))
    #_dept = db.relationship("Department", collection_class=attribute_mapped_collection('id'))
    datetime = db.Column('datetime', db.DateTime)
    
    def __init__(self, alarm, person, dept, participation=4, active=1, dt=''):
        self.participation = participation
        self.active = active
        self._alarm = alarm
        self._person = person
        self._dept = dept
        if dt == '':
            self.datetime = datetime.datetime.now()    
        else:
            self.datetime = dt   
        
    def getColor(self):
        """
        Get color of car, default *#ffffff*

        :return: colorcode
        """
        if self.participation == 0:
                return "#ff0000"
        if self.participation == 1:
                return "#00ff00"
        if self.participation == 2:
                return "#fcff00"
        #no feedback
        return "#a79c9c"
        
    def __str__(self):
        #return "Participation id=" + self.id + " active=" + self.active + " participation=" + self.participation + " datetime=" + self.datetime + " person=" + self._person + " alarm=" + self._alarm + " dept=" + self._dept
        return "todo implement me!"

    @staticmethod
    def yes(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=1).count()
      
    @staticmethod
    def no(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=0).count()
      
    @staticmethod
    def maybe(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=2).count()
    @staticmethod
    def unknown(alarmid):
        return Participation.query.filter_by(_alarm=int(alarmid), participation=4).count()
      
    def getParticipationCountYes (self):
        return Participation.query.filter_by(_alarm=int(self._alarm), participation=1).count()
      
    @staticmethod
    def getParticipation(id=0, alarmid=0, params=[]):
        """
        Get list of cars filtered by given parameters

        :param optional id: id of car or 0 for all cars
        :param optional deptid: only cars of department with given id
        :param optional params: *onlyactive*
        :return: list of :py:class:`emonitor.modules.cars.car.Car`
        """
        logger.info ("getParticipation alarmid=%s" %alarmid)
        if id != 0:
            return Participation.query.filter_by(id=int(id)).first()
        elif int(alarmid) != 0:
            return Participation.query.filter_by(_alarm=int(alarmid)).order_by('participation').all()
        else:
            #if 'onlyactive' in params:
                #return Car.query.filter_by(active=1).order_by('dept', 'name').all()
            #else:
            return Participation.query.order_by('alarm', 'participation').all()

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


class ParticipationWidget(MonitorWidget):
    """person participation widget for alarms"""
    template = 'widget.participation.html'
    size = (5, 1)

    def addParameters(self, **kwargs):
        self.params.update(kwargs)
