import pdb
from collections import OrderedDict
import re
import traceback
import difflib
import logging
import datetime
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from emonitor.modules.alarms.alarmutils import AlarmFaxChecker
from emonitor.modules.streets.street import Street
from emonitor.modules.streets.city import City
from emonitor.modules.cars.car import Car
from emonitor.modules.settings.department import Department
from emonitor.modules.alarmkeys.alarmkey import Alarmkey
from emonitor.modules.alarmobjects.alarmobject import AlarmObject
from emonitor.modules.alarms.alarmtype import AlarmType

logger = logging.getLogger(__name__)

__all__ = ['XmlAlarmFaxChecker']


class XmlAlarmFaxChecker(AlarmFaxChecker):
    """
    <ALARM time="">
      <EINSATZ>Brand Auto 1</EINSATZ>
      <STRASSE>Elsaesser Strasse</STRASSE>
      <ORTSTEIL>Kleinblittersdorf</ORTSTEIL>
      <GEMEINDE>Kleinblittersdorf</GEMEINDE>
      <LANDKREIS>Regionalverband Saarbruecken</LANDKREIS>
      <HINWEIS>Brand von 2 PKW, vermutl. auf franz. Seite</HINWEIS>
    </ALARM>

    """
    __name__ = "XML"
    __version__ = '0.1'

    fields = {}
    sections = OrderedDict()
    sections[u'Meldebild'] = (u'key', u'evalKey')
    sections[u'Einsatznr'] = (u'time', u'evalTime')
    sections[u'Ortsteil/Ort'] = (u'city', u'evalCity')
    sections[u'Stra\xdfe'] = (u'address', u'evalStreet')
    sections[u'Hinweis'] = (u'remark', u'')
    sections[u'Objekt'] = (u'key', u'evalObjectBMA')
    keywords = [u'<Alarm']
    #fuer Stichworte / keys (siehe alarm.py line 524
    translations = AlarmFaxChecker.translations + [u'_bab_', u'_train_', u'_street_', u'_default_city_', u'_interchange_', u'_kilometer_', u'_train_identifier_']

    def getEvalMethods(self):
        """get all eval methods of fax checker

        :return: list of names of eval methods
        """
        return [m for m in self.__class__.__dict__.keys() if m.startswith('eval')]

    # eval methods for fax text recognition
    @staticmethod
    def evalStreet(fieldname, **params):
        alarmtype = None
        options = []
        if 'alarmtype' in params:
            alarmtype = params['alarmtype']
        else:
            if 'alarmtype' in XmlAlarmFaxChecker().fields:
                alarmtype = XmlAlarmFaxChecker().fields['alarmtype'][0]

        if 'options' in params:
            options = params['options']

        streets = Street.getStreets()
        _str = XmlAlarmFaxChecker().fields[fieldname][0]
        if 'part' in options:  # addresspart, remove city names
            for c in City.getCities():
                if _str.endswith(c.name):
                    _str = _str.replace(c.name, '')
            pattern = re.compile(r'(?P<street>(^(\D+))) (?P<housenumber>(?P<hn>([0-9]{1,3}((\s?)[a-z])?)).*)'  # street with housenumber
                                 r'|((?P<streetname>((.*[0-9]{4})|(^(\D+)))))'
                                 r'|((?P<bab>((.*) (\>) )(?P<direction>(.*))))'  # highway
                                 r'|((.*) (?P<train>(KM .*).*))')  # train
        else:
            pattern = re.compile(r'(?P<street>(^(\D+))) (?P<housenumber>(?P<hn>([0-9]{1,3}((\s?)[a-z])?)).*)'  # street with housenumber
                                 r'|((?P<bab>A[0-9]{2,3} [A-Za-z]+) (?P<direction>(\D*))(( (?P<as>[0-9]*))|(.*)))'  # highway
                                 r'|((.*)(?P<train>(Bahnstrecke .*)) (?P<km>[0-9]+(.*)))'  # train
                                 r'|((?P<streetname>((.*[0-9]{4})|(^(\D+)))))'
                                 )

        m = pattern.match(_str)
        if m:
            if m.groupdict()['street'] or m.groupdict()['streetname']:  # normal street, fields: 'street', 'housenumber' with sub 'hn'
                repl = difflib.get_close_matches(m.groupdict()['street'] or m.groupdict()['streetname'], [s.name for s in streets], 1)
                #import pdb; pdb.set_trace()
                #pdb.set_trace()
                if len(repl) > 0:
                    _streets = [s for s in filter(lambda s: s.name == repl[0], streets)]
                    if len(_streets) > 0:
                        if XmlAlarmFaxChecker().fields['city'][1] != 0:  # city given
                            for _s in _streets:  # find correct city
                                if _s.city.id == XmlAlarmFaxChecker().fields['city'][1]:
                                    _street = _s
                                    _streets = [_s]
                                    break
                            XmlAlarmFaxChecker().fields[fieldname] = (_street.name, _street.id)
                            XmlAlarmFaxChecker().logger.debug(u'street: "{}" ({}) found'.format(_street.name, _street.id))
                        else:
                            XmlAlarmFaxChecker().fields[fieldname] = (m.groupdict()['street'] or m.groupdict()['streetname'], 0)
                            if not re.match(alarmtype.translation(u'_street_'), _str[1]) and 'part' not in options:  # ignore 'street' value and part-address
                                XmlAlarmFaxChecker().fields['streetno'] = (m.groupdict()['housenumber'], 0)

                    if m.groupdict()['hn'] and XmlAlarmFaxChecker().fields['city'][1] != 0:
                        if m.groupdict()['housenumber'] != m.groupdict()['housenumber'].replace('B', '6').replace(u'\xdc', u'0'):
                            _housenumber = m.groupdict()['housenumber'].replace('B', '6').replace(u'\xdc', u'0')
                            _hn = _housenumber
                        else:
                            _housenumber = m.groupdict()['housenumber'].replace('B', '6').replace(u'\xdc', u'0')
                            _hn = m.groupdict()['hn']
                        if m.groupdict()['hn']:
                            db_hn = filter(lambda h: h.number.replace(' ', '') == _hn.replace(' ', ''), _streets[0].housenumbers)
                            if len(db_hn) == 0:
                                db_hn = filter(lambda h: h.number == _hn.split()[0], _streets[0].housenumbers)
                            if len(db_hn) > 0:
                                XmlAlarmFaxChecker().fields['id.streetno'] = (db_hn[0].number, db_hn[0].id)
                                XmlAlarmFaxChecker().fields['streetno'] = (_housenumber, db_hn[0].id)
                                #XmlAlarmFaxChecker().fields['lat'] = (db_hn[0].points[0][0], db_hn[0].id)
                                #XmlAlarmFaxChecker().fields['lng'] = (db_hn[0].points[0][1], db_hn[0].id)
                                #cetner
                                XmlAlarmFaxChecker().fields['lat'] = (db_hn[0].center_geolocation()[0], db_hn[0].id)
                                XmlAlarmFaxChecker().fields['lng'] = (db_hn[0].center_geolocation()[1], db_hn[0].id)
                            elif _housenumber:
                                XmlAlarmFaxChecker().fields['streetno'] = (_housenumber, 0)
                                XmlAlarmFaxChecker().fields['lat'] = (_streets[0].lat, 0)
                                XmlAlarmFaxChecker().fields['lng'] = (_streets[0].lng, 0)
                            else:
                                XmlAlarmFaxChecker().fields['lat'] = (_streets[0].lat, 0)
                                XmlAlarmFaxChecker().fields['lng'] = (_streets[0].lng, 0)

            elif m.groupdict()['bab']:  # highway, fields: 'bab', 'direction', 'as'
                repl = difflib.get_close_matches(u"{} {}".format(m.groupdict()['bab'], m.groupdict()['direction']), [s.name for s in streets], 1)
                if len(repl) > 0:
                    _streets = [s for s in filter(lambda s: s.name == repl[0], streets)]
                    if len(_streets) > 0:
                        _street = _streets[0]
                        XmlAlarmFaxChecker().fields[fieldname] = (_street.name, _street.id)
                        XmlAlarmFaxChecker().logger.debug(u'street: "{}" ({}) found'.format(_street.name, _street.id))
                return

            elif m.groupdict()['train']:  # train, fields: 'train', 'km'
                repl = difflib.get_close_matches(m.groupdict()['train'], [s.name for s in streets], 1)
                if len(repl) > 0:
                    _streets = [s for s in filter(lambda s: s.name == repl[0], streets)]
                    if len(_streets) > 0:
                        _street = _streets[0]
                        XmlAlarmFaxChecker().fields[fieldname] = (_street.name, _street.id)
                        XmlAlarmFaxChecker().logger.debug(u'street: "{}" ({}) found'.format(_street.name, _street.id))

                return

            else:  # not found
                repl = difflib.get_close_matches(_str, [s.name for s in streets])
                if len(repl) >= 1:
                    try:
                        street_id = u';'.join([u'{}'.format(s.id) for s in filter(lambda s: s.name == repl[0], streets)])
                    except:
                        street_id = u''

                    XmlAlarmFaxChecker().fields[fieldname] = (u'{}'.format(repl[0]), street_id)
                    if 'streetno' not in XmlAlarmFaxChecker().fields or XmlAlarmFaxChecker().fields['streetno'] == u"":
                        XmlAlarmFaxChecker().fields['streetno'] = (u'{}'.format(u" ".join(_str[repl[0].count(u' ') + 1:])).replace(alarmtype.translation(u'_street_'), u'').strip(), street_id)
                return
        else:
            XmlAlarmFaxChecker().fields[fieldname] = (_str, 0)
            return

    @staticmethod
    def evalCity(fieldname, **params):
        if fieldname in XmlAlarmFaxChecker().fields:
            _str = XmlAlarmFaxChecker().fields[fieldname][0]
        else:  # city not found -> use default city
            city = City.getDefaultCity()
            XmlAlarmFaxChecker().fields[fieldname] = (city.name, city.id)
            #raise Exception()

        alarmtype = None
        if 'alarmtype' in params:
            alarmtype = params['alarmtype']
        else:
            if 'alarmtype' in XmlAlarmFaxChecker().fields:
                alarmtype = XmlAlarmFaxChecker().fields['alarmtype'][0]

        try:
            if _str.strip() == '':
                XmlAlarmFaxChecker().fields[fieldname] = ('', 0)
        except:
            logger.error (traceback.format_exc())

        cities = City.getCities()
        for city in cities:  # test first word with defined subcities of cities
            try:
                repl = difflib.get_close_matches(_str.split()[0], city.subcities + [city.name], 1, cutoff=0.7)
                if len(repl) > 0:
                    XmlAlarmFaxChecker().fields[fieldname] = (repl[0], city.id)
                    return
            except:
                pass

        for city in cities:  # test whole string with subcities
            repl = difflib.get_close_matches(_str, city.subcities + [city.name], 1)
            if len(repl) > 0:
                XmlAlarmFaxChecker().fields[fieldname] = (repl[0], city.id)
                return

        for s in _str.split():
            for c in cities:
                repl = difflib.get_close_matches(s, [c.name], 1, cutoff=0.7)
                if len(repl) == 1:
                    XmlAlarmFaxChecker().fields[fieldname] = (repl[0], c.id)
                    return

        if alarmtype.translation(u'_default_city_') in _str.lower():
            d_city = filter(lambda c: c.default == 1, cities)
            if len(d_city) == 1:
                XmlAlarmFaxChecker().fields[fieldname] = (d_city[0].name, d_city[0].id)
                return

            # use default city
            city = City.getDefaultCity()
            XmlAlarmFaxChecker().fields[fieldname] = (city.name, city.id)
            return

        if _str.startswith('in'):  # remove 'in' and plz
            _str = re.sub(r'in*|[0-9]*', '', _str[2:].strip())

        XmlAlarmFaxChecker().fields[fieldname] = (_str, 0)  # return original if no match
        return

    @staticmethod
    def evalAddressPart(fieldname, options="", **params):
        alarmtype = None
        options = []
        if 'alarmtype' in params:
            alarmtype = params['alarmtype']
        else:
            if 'alarmtype' in XmlAlarmFaxChecker().fields:
                alarmtype = XmlAlarmFaxChecker().fields['alarmtype'][0]

        if 'options' in params:
            options = params['options']
        _str = XmlAlarmFaxChecker().fields[fieldname][0].strip().replace(u'\r', u'').replace(u'\n', u'')
        XmlAlarmFaxChecker().fields[fieldname] = (_str, 0)
        options.append('part')
        params['options'] = filter(None, options)
        XmlAlarmFaxChecker().evalStreet(fieldname, **params)

        if _str.endswith(')') and alarmtype.translation(u'_interchange_') in _str:  # bab part found
            part = '{}'.format(_str[_str.rfind('(') + 1:-1].replace(u'\n', u' '))
            XmlAlarmFaxChecker().fields[fieldname] = (u'{}: {}'.format(alarmtype.translation(u'_kilometer_'), part), -1)
            if XmlAlarmFaxChecker().fields['address'][1] != 0:
                _streets = Street.getStreets(id=XmlAlarmFaxChecker().fields['address'][1])
                numbers = _streets.housenumbers
                hn = difflib.get_close_matches(part, [n.number for n in numbers], 1)
                XmlAlarmFaxChecker().fields['zoom'] = (u'14', 1)
                if len(hn) == 1:
                    nr = [n for n in numbers if n.number == hn[0]][0]
                    XmlAlarmFaxChecker().fields['streetno'] = (nr.number, nr.id)
                    XmlAlarmFaxChecker().fields['id.streetno'] = (nr.id, nr.id)
                    XmlAlarmFaxChecker().fields['lat'] = (nr.points[0][0], nr.id)
                    XmlAlarmFaxChecker().fields['lng'] = (nr.points[0][1], nr.id)
                return

        elif alarmtype.translation(u'_train_identifier_') in _str:  # found train position
            part = u'{}'.format(_str[_str.find(alarmtype.translation(u'_train_identifier_')):])
            XmlAlarmFaxChecker().fields[fieldname] = (u'{}'.format(part), 1)
            numbers = Street.getStreets(id=XmlAlarmFaxChecker().fields['address'][1]).housenumbers

            for nr in numbers:
                if part.startswith(nr.number):
                    XmlAlarmFaxChecker().fields['streetno'] = (nr.number, nr.id)
                    XmlAlarmFaxChecker().fields['id.streetno'] = (nr.id, nr.id)
                    XmlAlarmFaxChecker().fields['lat'] = (nr.points[0][0], nr.id)
                    XmlAlarmFaxChecker().fields['lng'] = (nr.points[0][1], nr.id)
                    XmlAlarmFaxChecker().fields['zoom'] = (u'15', 1)
                    return

        else:
            if XmlAlarmFaxChecker().fields[fieldname][1] != 0:
                return
            part = _str

        XmlAlarmFaxChecker().fields[fieldname] = (part, -1)
        return

    @staticmethod
    def evalKey(fieldname, **params):
        if fieldname in XmlAlarmFaxChecker().fields:
            _str = XmlAlarmFaxChecker().fields[fieldname][0]
        else:  # key not found
            XmlAlarmFaxChecker().fields[fieldname] = (u'----', 0)
            #raise Exception()
        if _str == '':
            XmlAlarmFaxChecker().fields[fieldname] = (_str, 0)
            return
        keys = {}
        try:
            for k in Alarmkey.getAlarmkeys():
                # z.B. 'Brand 3' = id
                keys[k.key] = k.id

            repl = difflib.get_close_matches(_str.strip(), keys.keys(), 1, cutoff=0.8)  # default cutoff 0.6
            if len(repl) == 0:
                repl = difflib.get_close_matches(_str.strip(), keys.keys(), 1)  # try with default cutoff
            if len(repl) > 0:
                k = Alarmkey.getAlarmkeys(int(keys[repl[0]]))
                XmlAlarmFaxChecker().fields[fieldname] = (u'{}: {}'.format(k.category, k.key), k.id)
                XmlAlarmFaxChecker().logger.debug(u'key: found "{}: {}"'.format(k.category, k.key))
                return
            #fix <STICHWORT>Brand 3 348 BMA RV</STICHWORT> matcht nicht
            for k in Alarmkey.getAlarmkeys():
                ms = "(?P<Key>(%s))[\s\d\D]*" % k.key
                rx  = re.compile (ms)
                logger.debug('re=%s str=%s' % (ms, _str.strip()))
                m = rx.match (_str.strip())
                #import pdb; pdb.set_trace()
                if m:
                    try:
                        if m.group('Key') == k.key:
                            XmlAlarmFaxChecker().fields[fieldname] = (u'{}: {}'.format(k.category, k.key), k.id)
                            XmlAlarmFaxChecker().logger.debug(u'key: found "{}: {}"'.format(k.category, k.key))
                            return
                    except IndexError:
                        pass
            XmlAlarmFaxChecker().logger.info(u'key: "{}" not found in alarmkeys'.format(_str))
            XmlAlarmFaxChecker().fields[fieldname] = (_str, 0)
        except:

            XmlAlarmFaxChecker().logger.error(u'key: error in key evaluation traceback\n%s' % traceback.format_exc())
        finally:
            return

    @staticmethod
    def evalObject(fieldname, **params):
        _str = XmlAlarmFaxChecker().fields[fieldname][0].replace('\xc3\x9c'.decode('utf-8'), u'0')
        objects = AlarmObject.getAlarmObjects()
        repl = difflib.get_close_matches(_str, [o.name for o in objects], 1)
        if repl:
            o = filter(lambda o: o.name == repl[0], objects)
            XmlAlarmFaxChecker().fields[fieldname] = (repl[0], o[0].id)
            XmlAlarmFaxChecker().logger.debug(u'object: "{}" objectlist -> {}'.format(_str, repl[0]))
        else:
            s = ""
            for p in _str.split():
                s += p
                repl = difflib.get_close_matches(s, [o.name for o in objects], 1)

                if len(repl) == 1:
                    o = filter(lambda o: o.name == repl[0], objects)
                    XmlAlarmFaxChecker().fields[fieldname] = (repl[0], o[0].id)
                    XmlAlarmFaxChecker().logger.debug(u'object: "{}" special handling -> {}'.format(_str, repl[0]))
                    return

            XmlAlarmFaxChecker().fields[fieldname] = (_str, 0)
        return


    @staticmethod
    #wird mit key als fieldname aufgerufen!
    def evalObjectBMA (fieldname, **params):
        logger.debug("evalObjectBMA")
        _str = XmlAlarmFaxChecker().fields[fieldname][0].replace('\xc3\x9c'.decode('utf-8'), u'0')
        objects = AlarmObject.getAlarmObjects()
        #import pdb; pdb.set_trace()
        #key suche nach BMA Nummer
        for o in objects:
            logger.debug("object " + str(o.id) + " / " + o.name)
            if o.bma in _str:
                logger.debug("Alarmobjekt %s (BMA: %s) gefunden! " % (o.name, o.bma))
                #BMA Nummer gefunden
                XmlAlarmFaxChecker().fields[u'object'] = (o, o.id)
                XmlAlarmFaxChecker().logger.debug(u'object: "{}" special handling (BMA) -> {}'.format(_str, o.bma))
                return
        #XmlAlarmFaxChecker().fields[u'object'] = (_str, 0)
        logger.debug("KEIN Alarmobjekt gefunden!")
        return



    def buildAlarmFromText(self, alarmtype, rawtext):
        logger.debug ("buildAlarmFromText %s %s" % (alarmtype, rawtext))

        values = {}

        if alarmtype:
            sections = alarmtype.getSections()
            sectionnames = dict(zip([s.name for s in sections], [s.key for s in sections]))
            sectionmethods = dict(zip([s.key for s in sections], [s.method for s in sections]))
            XmlAlarmFaxChecker().fields['alarmtype'] = (alarmtype, 0)
        else:  # matching alarmtype found
            return values



        #xmlstr = '<ALARM time="2016-02-03 00:13:00.353528">
        #<STICHWORT>Brand Auto 1</STICHWORT>
        #<STRASSE>Elsaesser Strasse</STRASSE>
        #<ORTSTEIL>Kleinblittersdorf</ORTSTEIL>
        #<GEMEINDE>Kleinblittersdorf</GEMEINDE>
        #<LANDKREIS>Regionalverband Saarbruecken</LANDKREIS>
        #<HINWEIS>Brand von 2 PKW, vermutl. auf franz. Seite</HINWEIS>
        #</ALARM>'

        #xmlstr = '<ALARM time="2016-02-03 00:13:00.353528"> <EINSATZ>Brand Auto 1</EINSATZ><STRASSE>Elsaesser Strasse</STRASSE><ORTSTEIL>Kleinblittersdorf</ORTSTEIL>      <GEMEINDE>Kleinblittersdorf</GEMEINDE>      <LANDKREIS>Regionalverband Saarbruecken</LANDKREIS>      <HINWEIS>Brand von 2 PKW, vermutl. auf franz. Seite</HINWEIS></ALARM>'

        xmlstr = rawtext
        #xmlstr = escape (xmlstr)

        logger.debug ("starting xml parsing")
        try:
            root = ET.fromstring (xmlstr)
        except ET.ParseError:
            import traceback
            XmlAlarmFaxChecker().logger.error(u'error parsing the xml {}\n'.format(traceback.format_exc()))
            logger.info ("XML string = %s" % xmlstr)
            return values

        if root.tag == 'ALARM':
            dt = datetime.datetime.now()
            try:
                xdt = datetime.datetime.strptime (root.attrib['time'], '%Y-%m-%d %H:%M:%S.%f')
                if datetime.datetime.now() - xdt > datetime.timedelta(hours=1):
                    logger.debug ('XML alarm time too old (%s) -> using now(%s)' % (xdt, dt))
                else:
                    dt = xdt
            except ValueError:
                pass
            values['time'] = {0:dt.strftime ('%d.%m.%Y - %H:%M:%S') , 1:1}
            #for child in root:
                #print ("%s %s" % (child.tag, child.attrib))
            einsatz = ''
            try:
                einsatz = root.find('STICHWORT').text
            except AttributeError:
                pass
            self.fields['key'] = {0:einsatz , 1:0}
            #incl BMA Zusatz
            self.fields['key_untouched'] = {0:einsatz , 1:0}

            strasse = ''
            try:
                strasse = root.find('STRASSE').text
            except AttributeError:
                pass
            self.fields['address'] = {0:strasse, 1:0}

            ortsteil = ''
            try:
                ortsteil = root.find('ORTSTEIL').text
            except AttributeError:
                pass
            self.fields['district'] = { 0:ortsteil , 1:0 }

            gemeinde = ''
            try:
                gemeinde = root.find('GEMEINDE').text
            except AttributeError:
                pass
            self.fields['city'] = { 0:gemeinde , 1:1 }

            landkreis = ''
            try:
                landkreis = root.find('LANDKREIS').text
            except AttributeError:
                pass

            hinweis = ''
            try:
                hinweis = root.find('HINWEIS').text
            except AttributeError:
                pass
            self.fields['remark'] = {0:hinweis, 1:0}
            #BMA verantwortlicher
            self.fields['person'] = {0:hinweis, 1:0}

            original = ''
            try:
                original = root.find('ORIGINAL').text
                original = original.replace ('&lt;', '<')
                original = original.replace ('&gt;', '>')
                original = original.replace ('&amp;', '')
            except AttributeError:
                pass
            self.fields['original'] = {0:original, 1:0}

            self.evalKey ('key')
            self.evalCity('city')
            self.evalStreet('address')
            #TODO evalObject TEST
            self.evalObjectBMA  ('key_untouched')

        for k in XmlAlarmFaxChecker().fields:
            try:
                values[k] = (XmlAlarmFaxChecker().fields[k][0].decode('utf-8'), XmlAlarmFaxChecker().fields[k][1])
            except:
                values[k] = (XmlAlarmFaxChecker().fields[k][0], XmlAlarmFaxChecker().fields[k][1])
        return values
