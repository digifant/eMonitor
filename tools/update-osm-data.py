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
import sys
import pdb
import argparse
from pprint import pprint

def osmWebUrl (lat,lng):
    return "http://www.openstreetmap.org/?&mlat=%s&mlon=%s&zoom=17" % (lat,lng)

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1', 'j', 'ja'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0', 'nein'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def prompt(query):
   sys.stdout.write('%s [y/n]: ' % query)
   val = raw_input()
   try:
       ret = str2bool(val)
   except ValueError:
       sys.stdout.write('Please answer with a y/n\n')
       return prompt(query)
   return ret

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
                print ("Street DB %s lat=%s lng=%s" % (row[1].decode('iso-8859-1').encode('utf8'), row[5], row[6]) )
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


def verifyMysqlStreets (db, user, passwd, command, street=-1):
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

    if command == "verify_streets":
        sql = "SELECT * FROM streets"
        if street > 0:
            sql = sql + " where id=%i" % street

        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                print ("Street %s lat=%s lng=%s url=%s" % (row[1].decode('iso-8859-1').encode('utf8'), row[5], row[6], osmWebUrl(row[5],row[6]) ) )
                if ( row[0] > 0 ):
                    _position = queryOsmNominatin (street=row[1].decode('iso-8859-1').encode('utf8'), streetno='', city='Kleinblittersdorf')
                    if _position != None:
                        sql = 'update streets set lat=%s, lng=%s, osmid=%s where id = %s' % (float(_position['lat']), float(_position['lng']), int(_position['osm_id']), int(row[0]))
                        logging.debug ("sql query %s" % sql)
                        if row[9] == int(_position['osm_id']):
                            logging.info ("osmid=%s db lat=%s db lng=%s OsmNominatim lat=%s lng=%s new url=%s" % (row[9], row[5], row[6], float(_position['lat']), float(_position['lng']), osmWebUrl(float(_position['lat']),float(_position['lng'])) ) )
                            if round(float(row[5]),4) != round(float(_position['lat']),4) or round(float(row[6]),4) != round(float(_position['lng']),4):
                                logging.info ("%i NO MATCH" % row[9])
                                if options.ask_fix and prompt ("Fix?"):
                                    try:
                                        cursor.execute(sql)
                                        db.commit()
                                        logging.info ("street %s updated lat, lng, osmid to (%s,%s,%s)" % (row[1].decode('iso-8859-1').encode('utf8'), float(_position['lat']), float(_position['lng']), (_position['osm_id'])))
                                    except:
                                        db.rollback()
                                        logging.error ("SQL Error %s" % traceback.format_exc())
                            else:
                                logging.info ("%i MATCH" % row[9])
                        else:
                            logging.fatal ("OSMID stimmt nicht überein! %s vs %s url=%s" % (row[9], _position['osm_id'], osmWebUrl(float(_position['lat']),float(_position['lng']))))
                            if options.ask_fix and prompt ("Fix?"):
                                try:
                                    cursor.execute(sql)
                                    db.commit()
                                    logging.info ("street %s updated lat, lng, osmid to (%s,%s,%s)" % (row[1].decode('iso-8859-1').encode('utf8'), float(_position['lat']), float(_position['lng']), (_position['osm_id'])))
                                except:
                                    db.rollback()
                                    logging.error ("SQL Error %s" % traceback.format_exc())
                    else:
                        logging.fatal ("OSM nominatin Query failed!")
                        not_found[row[0]] = row[1].decode('iso-8859-1').encode('utf8')

                    #No heavy uses (an absolute maximum of 1 request per second).
                    #http://wiki.openstreetmap.org/wiki/Nominatim_usage_policy
                    time.sleep (1)


        except:
            logging.error ("DB Error %s" % traceback.format_exc() )

    # disconnect from server
    db.close()

    logging.info ("verify finished")



if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--database", dest="database", help="mysql database name", default="emonitor")
    parser.add_option("-u", "--user", dest="user", help="mysql user", default='emonitor')
    parser.add_option("-p", "--passwd", dest="passwd", help="mysql password", default='emonitor')
    parser.add_option("--update-streets-position", dest="update_streets_position", help="update positions for all streets",  action="store_true", default=False)
    parser.add_option("--verify-street-position", dest="verify_street_position", help="verify positions for given street",  type=int, default=-1)
    parser.add_option("-v", "--verify-all-streets-position", dest="verify_all_streets_position", help="verify positions for given street",  action="store_true", default=False)
    parser.add_option("-a", "--ask-fix", dest="ask_fix", help="ask for fixing",  action="store_true", default=False)

    (options, args) = parser.parse_args()

    #logging.basicConfig(filename='screenshot-and-telegram.log', level=logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    if options.update_streets_position:
        updateMysqlStreets (db=options.database, user=options.user, passwd=options.passwd, command="update_position")

    if options.verify_street_position > 0:
        verifyMysqlStreets (db=options.database, user=options.user, passwd=options.passwd, command="verify_streets", street=int(options.verify_street_position))

    if options.verify_all_streets_position:
        verifyMysqlStreets (db=options.database, user=options.user, passwd=options.passwd, command="verify_streets")

    #queryOsmNominatin(street="Rexrothstraße", streetno='', city='Kleinblittersdorf')
