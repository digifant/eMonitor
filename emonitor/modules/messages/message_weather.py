import datetime
import urllib2, urllib, json
from flask import render_template
from emonitor.widget.monitorwidget import MonitorWidget
from emonitor.extensions import babel
from emonitor.modules.settings.settings import Settings
import logging
import traceback

__all__ = ['WeatherWidget']

babel.gettext('Mon')
babel.gettext('Tue')
babel.gettext('Wed')
babel.gettext('Thu')
babel.gettext('Fri')
babel.gettext('Sat')
babel.gettext('Sun')
babel.gettext('message.weather')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not 'LASTCALL' in globals():
    LASTCALL=None
if not 'WEATHERDATA' in globals():
    WEATHERDATA=None


class WeatherWidget(MonitorWidget):
    """Weather widget for monitors"""
    __info__ = {'icon': 'fa-cloud'}
    __fields__ = ['weather.location', 'weather.icons', 'weather.forecast']
    template = 'widget.message.weather.html'
    size = (5, 4)
    data = None

    def __repr__(self):
        return "weather"

    def getAdminContent(self, **params):
        """Deliver admin content for current message module"""
        params.update({'settings': Settings})
        return render_template('admin.message.weather.html', **params)

    def getMonitorContent(self, **params):
        """Deliver monitor content for current message module"""
        self.addParameters(**params)
        return self.getHTML('', **params)

    def getEditorContent(self, **params):
        """Deliver editor content for current message module"""
        params.update({'settings': Settings})
        return render_template('frontend.messages_edit_weather.html', **params)

    def addParameters(self, **kwargs):
        """
        Add special parameters for weather widget *messages.weather.\**
        check https://developer.yahoo.com/yql/console/ for online editor

        :param kwargs: list of parameters for update
        """
        global LASTCALL
        global WEATHERDATA

        if 'message' in kwargs:
            location = kwargs['message'].attributes['weather.location']
            icons = kwargs['message'].attributes['weather.icons']
            forecast = kwargs['message'].attributes['weather.forecast']
        else:
            location = Settings.get('messages.weather.location')
            icons = Settings.get('messages.weather.icons')
            forecast = Settings.get('messages.weather.forecast')

        if not LASTCALL or datetime.datetime.now() > LASTCALL + datetime.timedelta(hours=1):
            try:
                # reload data from web
                compass = ['N', 'NNO', 'NO', 'ONO', 'O', 'OSO', 'SO', 'SSO', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N']
                baseurl = "https://query.yahooapis.com/v1/public/yql?"
                yql_query = u'select * from weather.forecast where woeid in (select woeid from geo.places(1) where text="{}") and u="c"'.format(location).encode('utf-8')
                yql_url = baseurl + urllib.urlencode({'q': yql_query}) + "&format=json"
                #https://query.yahooapis.com/v1/public/yql?q=select+%2A+from+weather.forecast+where+woeid+in+%28select+woeid+from+geo.places%281%29+where+text%3D%22Kleinblittersdorf%22%29+and+u%3D%22c%22&format=json
                #https://developer.yahoo.com/weather/documentation.html
                try:
                    result = urllib2.urlopen(yql_url).read()
                    self.data = json.loads(result)
                    self.data = self.data['query']['results']['channel']
                except (urllib2.URLError, TypeError):
                    logger.warn(traceback.format_exc())
                    logger.warn("query url: %s" % yql_url )
                    self.data = {}
                try:
                    self.data['wind']['directionstring'] = compass[int(int(self.data['wind']['direction']) / 22.5)]
                except (ValueError, KeyError) as e:
                    self.data['wind'] = {}
                    self.data['wind']['directionstring'] = ""

                try:
                    if float ( self.data['atmosphere']['pressure'] ) > 1200:
                        #bug, yahoo returns sometimes ca 33000 hPa -> set it to 0
                        self.data['atmosphere']['pressure'] = "0"
                except (ValueError, KeyError) as e:
                        self.data['atmosphere']['pressure'] = "0"

                if 'astronomy' not in self.data:
                    self.data['astronomy'] = {'sunrise': {}, 'sunset': {}}
                if 'am' in self.data['astronomy']['sunrise']:
                    self.data['astronomy']['sunrise'] = self.data['astronomy']['sunrise'][:-3]
                if 'pm' in self.data['astronomy']['sunset']:
                    self.data['astronomy']['sunset'] = self.data['astronomy']['sunset'][:-3].split(':')
                    self.data['astronomy']['sunset'][0] = "%s" % (12 + int(self.data['astronomy']['sunset'][0]))
                    self.data['astronomy']['sunset'] = ':'.join(self.data['astronomy']['sunset'])
                LASTCALL = datetime.datetime.now()
                WEATHERDATA=self.data

                try:
                    self.data['lastBuildDate'] = datetime.datetime.strptime(self.data['lastBuildDate'][:-5], '%a, %d %b %Y %I:%M %p').strftime('%d.%m.%Y %H:%M')
                except (ValueError, KeyError):
                    self.data['lastBuildDate'] = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
            except:
                logger.error (traceback.format_exc())
                self.data = {}
                self.data['wind'] = {}
                self.data['wind']['directionstring'] = ""
                self.data['astronomy'] = {'sunrise': {}, 'sunset': {}}
                LASTCALL = None
                WEATHERDATA = None
        else:
            self.data = WEATHERDATA
        kwargs.update({'location': location, 'icons': icons, 'forecast': forecast, 'data': self.data})
        self.params = kwargs
