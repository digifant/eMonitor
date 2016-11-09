import yaml
import logging
from datetime import datetime
from emonitor.extensions import db
from sqlalchemy.orm.collections import attribute_mapped_collection
from emonitor.modules.settings.settings import Settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class Person(db.Model):
    """Person class"""
    __tablename__ = 'persons'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(64))
    lastname = db.Column(db.String(64))
    salutation = db.Column(db.String(16))
    grade = db.Column(db.String(32))
    position = db.Column(db.String(32))
    identifier = db.Column(db.String(32))
    active = db.Column(db.BOOLEAN)
    asgt = db.Column(db.BOOLEAN)
    groupLeader = db.Column(db.BOOLEAN)
    platoonLeader = db.Column(db.BOOLEAN)
    birthdate = db.Column(db.DATETIME)
    remark = db.Column(db.TEXT)
    telegramId = db.Column(db.String(64))
    _dept = db.Column('dept', db.ForeignKey('departments.id'))
    _options = db.Column('options', db.TEXT)

    dept = db.relationship("Department", collection_class=attribute_mapped_collection('id'))

    def __init__(self, firstname, lastname, salutation, grade, position, identifier, active, asgt, groupLeader, platoonLeader, birthdate, remark, telegramId, dept, **options):
        self.firstname = firstname
        self.lastname = lastname
        self.salutation = salutation
        self.grade = grade
        self.position = position
        self.identifier = identifier
        self.active = active
        self.asgt = asgt
        self.groupLeader = groupLeader
        self.platoonLeader = platoonLeader
        self.birthdate = birthdate
        self.remark = remark
        self.telegramId = telegramId
        self._dept = dept
        self._options = yaml.safe_dump(options, encoding='utf-8')

    @property
    def fullname(self):
        """format fullname"""
        return u"{}, {}".format(self.lastname, self.firstname)

    @property
    def age(self):
        """calculate age in years"""
        return int(round((datetime.now() - self.birthdate).days / 365.25, 0))

    @property
    def birthday(self):
        """
        calculate day of birthdate for sorting
        caution: use the same year for day calculation (1900)
        """
        return int((datetime(1904, *self.birthdate.timetuple()[1:-2])).strftime('%j'))

    @staticmethod
    def getPersons(id=0, identifier=0, dept=0, onlyactive=False, qtelegramId=''):
        if id != 0:
            return Person.query.filter_by(id=id).first()
        elif identifier != 0:
            return Person.query.filter_by(identifier=identifier).first()
        elif dept != 0:
            if onlyactive:
                return Person.query.filter_by(_dept=dept, active=True).order_by('lastname').all()
            return Person.query.filter_by(_dept=dept).order_by('lastname').all()
        elif qtelegramId != '':
            return Person.query.filter_by(telegramId=qtelegramId).first()
        else:
            if onlyactive:
                return Person.query.filter_by(active=True).order_by('lastname').all()
            return Person.query.order_by('lastname').all()

    @staticmethod
    def settings():
        return dict(Settings.getYaml('persons.settings'))
