#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import traceback
import os
import time
from optparse import OptionParser
import MySQLdb
import codecs
import requests
from pprint import pprint


# returns None if not found!
def queryOsmNominatin(street, streetno, city ):
    url = 'http://nominatim.openstreetmap.org/search'
    params = 'format=json&city={}&street={}'.format(city, street)
    #params = 'format=json&city=%s&street=%s' % (city, address)
    if streetno != '':
        params += ' {}'.format(streetno)
    params = params.replace (' ', '+')
    params = params.replace ('<', '&lt;')
    params = params.replace ('>', '&gt;')
    logging.debug ("OSM nominatim query: %s?%s" % (url,params))
    headers = {
        'User-Agent': 'OSMSyncForFireFighterStreetDbOfOurTown',
        'From': 'bofhnospam@koffeinbetrieben.de'
    }
    r = requests.get('{}?{}'.format(url, params), timeout=3, headers=headers)
    #logging.debug("osm nomination result: %s" % pprint(r.json()))
    #import pdb; pdb.set_trace()
    _position = None
    try:
        _position = {'lat':r.json()[0]['lat'], 'lng':r.json()[0]['lon'], 'osm_id':r.json()[0]['osm_id'].decode('iso-8859-1').encode('utf8') }
    except IndexError:
            logging.error ("street %s not found! (housenumber=%s)" % (street, streetno))
    #logging.debug (_position)
    return _position
    

def updateMysqlStreets (db, user, passwd, command):
    # Open database connection
    db = MySQLdb.connect("localhost",user,passwd,db )

    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # execute SQL query using execute() method.
    cursor.execute("SELECT VERSION()")

    # Fetch a single row using fetchone() method.
    data = cursor.fetchone()

    print "Database version : %s " % data
    
    not_found = {}
    
    if command == "update_position":
        sql = "SELECT * FROM streets"        
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                print ("Street %s lat=%s lng=%s" % (row[1].decode('iso-8859-1').encode('utf8'), row[5], row[6]) )
                if ( row[0] > 0 ):
                    _position = queryOsmNominatin (street=row[1].decode('iso-8859-1').encode('utf8'), streetno='', city='Kleinblittersdorf')
                    #No heavy uses (an absolute maximum of 1 request per second).
                    #http://wiki.openstreetmap.org/wiki/Nominatim_usage_policy
                    time.sleep (1)
                    if _position != None:
                        if row[9] == int(_position['osm_id']):
                            sql = 'update streets set lat=%s, lng=%s where id = %s' % (float(_position['lat']), float(_position['lng']), int(row[0]))
                            logging.debug ("sql query %s" % sql)
                            try:
                                cursor.execute(sql)
                                db.commit()
                                logging.info ("street %s updated lat and lng to (%s,%s)" % (row[1].decode('iso-8859-1').encode('utf8'), float(_position['lat']), float(_position['lng'])))
                            except:
                                db.rollback()
                                logging.error ("SQL Error %s" % traceback.format_exc())
                        else:
                            logging.fatal ("OSMID stimmt nicht überein! %s vs %s" % (row[9], _position['osm_id'] ))
                    else:
                        logging.fatal ("OSM nominatin Query failed!")
                        not_found[row[0]] = row[1].decode('iso-8859-1').encode('utf8') 
                    
        except:
            logging.error ("DB Error %s" % traceback.format_exc() )

    # disconnect from server
    db.close()
    
    logging.info ("Sync finished")
    if len(not_found) > 0:
        logging.error ("didnt found %s streets:" % len(not_found))
        for k in not_found.keys():
            logging.error ("not found: id=%s streetname=%s" % (k, not_found[k]))



if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--database", dest="database", help="mysql database name", default="emonitor")
    parser.add_option("-u", "--user", dest="user", help="mysql user", default='emonitor')
    parser.add_option("-p", "--passwd", dest="passwd", help="mysql password", default='emonitor')
    parser.add_option("--update-streets-position", dest="update_streets_position", help="update positions for all streets",  action="store_true", default=False)
        
    (options, args) = parser.parse_args()
        
    #logging.basicConfig(filename='screenshot-and-telegram.log', level=logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
        
    if options.update_streets_position:
        updateMysqlStreets (db=options.database, user=options.user, passwd=options.passwd, command="update_position")
    
    #queryOsmNominatin(street="Rexrothstraße", streetno='', city='Kleinblittersdorf')
