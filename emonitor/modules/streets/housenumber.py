import yaml
from math import cos, sin, atan2, sqrt, radians, degrees
from emonitor.extensions import db


class Housenumber(db.Model):
    """Housenumber class"""
    __tablename__ = 'housenumbers'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    streetid = db.Column(db.Integer, db.ForeignKey('streets.id'))
    number = db.Column(db.String(10))
    _points = db.Column('points', db.Text)
    street = db.relationship("Street", backref="streets", lazy='joined')

    def __init__(self, streetid, number, points):
        self.streetid = streetid
        self.number = number
        self._points = points

    @property
    def points(self):
        """
        Get points for housenumber

        :return: yaml structure with point positions
        """
        return yaml.load(self._points)

    @staticmethod
    def getHousenumbers(id=0):
        """
        Get list of all housenumbers, filtered by paramters

        :param optional id: id of housenumber, *0* for all
        :return: list of :py:class:`emonitor.modules.streets.housenumber.Housenumber`
        """
        if id == 0:
            return Housenumber.query.order_by(Housenumber.number).all()
        else:
            return Housenumber.query.filter_by(id=id).one()

    def center_geolocation(self):
        """
        Provide a relatively accurate center lat, lon returned as a list pair
        """
        geolocations = self.points
        
        x = 0
        y = 0
        z = 0

        for lat, lon in geolocations:
            lat = radians (float(lat))
            lon = radians (float(lon))
            x += cos(lat) * cos(lon)
            y += cos(lat) * sin(lon)
            z += sin(lat)

        x = float(x / len(geolocations))
        y = float(y / len(geolocations))
        z = float(z / len(geolocations))

        return (degrees(atan2(z, sqrt(x * x + y * y))), degrees(atan2(y, x)))
    
    def getPosition(self, index=0):
        try:
            p = self.points[index]
            #return dict(lat=p[0], lng=p[1])
            return self.center_geolocation ()
        except:
            return dict(lat=self.street.lat, lng=self.street.lng)
