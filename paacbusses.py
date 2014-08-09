import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from repoze.lru import lru_cache

# Errors

class BustimeError(Exception): pass
class RouteNotFoundError(BustimeError, ValueError): pass
class NoBusPrediction(Warning): pass

# Various hidden API endpoints            
API_BUS = "http://realtime.portauthority.org/bustime/map/getBusPredictions.jsp?bus=%s"
API_ONROUTE = "http://realtime.portauthority.org/bustime/map/getBusesForRoute.jsp?route=%s"
API_ETA = "http://realtime.portauthority.org/bustime/eta/getStopPredictionsETA.jsp?route=%s&stop=%s"
API_ROUTE = "http://realtime.portauthority.org/bustime/map/getStopsForRouteDirection.jsp?route=%s&direction=%s"
API_STOP = "http://realtime.portauthority.org/bustime/map/getStopPredictions.jsp?route=%s&stop=%s"

# List of error messages
ERRORS = {
    'bad_info': 'The Port Authority API is not returning information on the correct route.',
    'no_busses': 'There are no busses reported on this route right now.',
    'invalid_id': 'There is no data currently being reported for this route.'
}

# Objects

class Bus(object):
    """
    A `Bus` represents a single vehicle on a certain route with a definite location.
    
    Since a bus has a definite location, it has an associated `when` time that represents
    the time at which the location was gathered. A Bus also has a direction, represented by
    whether or not `outbound` is True (away from downtown) or False (to downtown).
    """
    
    @classmethod
    def fromxml(_class, element):
        """Turns an XML <bus> element into an object."""
        busid = element.find('id').text
        loc = tuple(map(float, (element.find("lat").text, element.find("lon").text)))
        if element.find("dd") == 'OUTBOUND':
            outbound = True
        else:
            outbound = False
        dest = element.find("fs").text
        route = element.find("rt").text
        
        return _class(busid, route, loc, outbound, dest)

    def __init__(self, id, route, loc, direction, dest):
        self.id = id
        assert type(loc) is tuple
        self.loc = loc
        self.outbound = direction
        self.dest = dest
        self.route = route
        self.when = datetime.now()

    def freshness(self):
        return (datetime.now() - self.when).seconds

    def __repr__(self):
        return "<Bus #%s route='%s %s' - currently @ %s - freshness %ss>" % (self.id, self.route, self.dest, self.loc, self.freshness())
        
    def __eq__(self, other):
        return self.id == other.id
        
class Route(object):
    """
    A `Route` represents one route (e.g. P1). It can be served by one or more busses
    and services a list of stops.
    """
    
    def __init__(self, routenum, stops, busses):
        self.routenum = routenum
        self.stops = stops
        self._busses = busses
    
    def __repr__(self):
        return "Route(%s)" % self.routenum
        
    def __str__(self):
        return self.__repr__()
    
    def __eq__(self, other):
        return self.routenum == other.routenum
    
    @property
    def busses(self):
        # Deal with generator exhaustion
        if type(self._busses) != list:
            self._busses = list(self._busses)
        return self._busses
    
    def update(self):
        """Refresh information about busses on the route."""
        logging.getLogger(__name__).debug("Updating information on busses...")
        self._busses = get_busses_on_route(self.routenum)
        
class Stop(object):
    """
    A `Stop` represents a single bus stop in a certain location. Each Stop has an 
    `id`, assigned by the transit operator, and can be served by Routes.
    
    Stops can grab a list of arriving busses by calling the `update_arrivals` method,
    or optionally setting `fetch` to True when creating a Stop.

    Example: Penn Ave at Friendship is stop 9186.
    """
    def __init__(self, id, text="Unnamed Stop", fetch=False):
        self.id = id
        self.text = text
        if fetch:
            self.arriving_busses = get_stop_prediction(self.id)
        else:
            self.arriving_busses = False    
        
    def __repr__(self):
        return "Stop(%s)" % self.id
    
    def __str__(self):
        return "Stop #%s - %s" % (self.id, self.text)
    
    def __eq__(self, other):
        return self.id == other.id
    
    def on_route(self, route):
        """Returns whether or not `route` is currently serving this stop."""
        if self.arriving_busses:
            return any(str(getattr(p, "route")) == route for p in self.arriving_busses) 
        
    def update_arrivals(self):
        """Refresh the list of arrivals at the stop."""
        logging.getLogger(__name__).debug("Updating information on bus arrivals at %s..." % self)
        self.arriving_busses = get_stop_prediction(self.id)
                
class Prediction(object): 
    """
    A `Prediction` represents one estimate of a bus arrival time at a `Stop`
    and has an arrival ETA (represented as a `datetime.timedelta`). Each `Prediction`
    applies to one `stop` and one `route` only.
    
    The `arriving_in` method can be used as a rough estimate of ETA after the initial
    prediction is grabbed, but predictions can change on the server side due to stops, 
    traffic, and so on. Because of this, it's probably better to update a stop's predictions
    periodically.
    """
    
    def __init__(self, timestring, route, stop):
        self.arrival = self.parse_time(timestring)
        self.route = route
        self.stop = Stop(stop, text=stopname(stop))
        self.when = datetime.now()
    
    @classmethod
    def parse_time(self, timestring):
        """Parses a tuple like ('5', 'MINUTES') into a timedelta."""
        
        number, unit = timestring[0], timestring[1].lower()
        if '&nbsp;' in number and 'approaching' in unit:
            # Instead of something like <3> <MINUTES>, an arriving bus
            # shows up as < > <APPROACHING> in the XML.
            arriving = True
        else:    
            number = int(number)
            if 'minute' in unit:
                arriving = timedelta(minutes=number)
            elif 'second' in unit:
                arriving = timedelta(seconds=number)
            elif 'hour' in unit:
                arriving = timedelta(hours=number)
            else:
                raise ValueError("%s is not a valid time interval." % timestring)    
    
        return arriving    
        
    def freshness(self):
        """Time since data point downloaded."""
        return (datetime.now() - self.when).seconds    
        
    def arriving_in(self):    
        """Returns difference between now and ETA when data was downloaded."""
        if self.arrival == True:
            return timedelta(seconds=0)
        else:    
            return (self.when + self.arrival) - datetime.now()

    def __repr__(self):
        return self.__str__()
    
    def __str__(self):        
        return "<Prediction for route=%s arriving at %s in %s - freshness %s>" % (self.route, self.stop, self.arriving_in(), self.freshness())   

class BusPrediction(Prediction):        
    """
    Predicted arrival of a specific bus at a stop (instead of for
    a specifc stop).
    """
    def __init__(self, arrival, busid, stop):
        self.arrival = self.parse_time(arrival)
        self.when = datetime.now()
        self.stop = stop
        # TODO: Lookup bus info by ID?
        self.bus = busid

# Helper functions
def grabxml(url):
    """Returns an ElementTree of an XML document at `url`."""
    return ET.fromstring ( requests.get(url).content )

@lru_cache(500)
def stopname(stopid):
    """Gets the name for a certain stop ID."""
    parser = grabxml( API_STOP % ("all", stopid) )
    return parser.find('nm').text
    
# Main functions

def get_route(routenum):
    """
    Returns a `Route` for `routenum` populated with a list of
    busses on the route and stops that the route serves.
    """
    busses = get_busses_on_route(routenum)
    stops = get_stops_for_route(routenum)
    return Route(routenum, stops, busses)
    
def get_busses_on_route(routenum):
    """
    Returns a list of busses currently trackable on a certain `routenum`.
    Each bus will have location data.
    """
    parser = grabxml(API_ONROUTE%routenum)
    
    if not parser.find('bus'):
        raise RouteNotFoundError(ERRORS['no_busses'])
    elif not parser.get('rt') == str(routenum):
        raise BustimeError(ERRORS['bad_info'])
    else:
        for bus in parser.findall("bus"):
            yield Bus.fromxml(bus)
        
@lru_cache(100)
def get_stops_for_route(routenum, outbound=True):
    """
    Get a list of all stops on a route given a `routenum`.  Set `outbound`
    to False to get a list of stops on a route's run towards downtown. 
    
    Each stop contains an `arriving_busses` attribute that represents a generator
    of predicted ETAs.
    """
    direction = "OUTBOUND" if outbound else "INBOUND"
    parser = grabxml( API_ROUTE%(routenum,direction) )
    
    if parser.find('id').text != str(routenum): 
        raise BustimeError(ERRORS['bad_info'])
    elif not parser.find('stops').find('stop'):
        raise RouteNotFoundError(ERRORS['invalid_id'])
    else:
        stops = {}
        for stop in parser.find('stops').findall('stop'):
            name, stop_id = stop.find('name').text, stop.find('id').text
            if name and stop_id:
                stops[int(stop_id)] = Stop(stop_id, text=name, fetch=True)
        if stops:
            logging.getLogger(__name__).debug("Found %s stops on route" % len(stops.keys()))
            return stops
        else:
            raise BustimeError("There are no stops listed for this route.")  
            
def get_stop_prediction(stop_id, route="all"):
    """
    Get bus ETA data for a certain `stop_id`.  Returns a `Prediction`.
    Data defaults to predictions on all routes (`route = "all"`) but a
    a specific route can be selected for by passing the `route` kwarg.
        """
    parser = grabxml( API_ETA % (route, stop_id) )
    
    if parser.find("noPredictionmessage"):
        raise NoBusPrediction()
    else:    
        for prediction in parser.findall('pre'):
            timestring = (prediction.find('pt').text, prediction.find('pu').text)
            routenum = prediction.find('rn').text
            yield Prediction(timestring, routenum, stop_id)

def get_bus_prediction(busid):
    """
    Get arrival predictions for a particular bus. Not sure how helpful this 
    is (unless you want to know how long it'll take for the bus you're on to
    get to a specific stop?). 
    
    From what I can tell, Port Authority limits data to the three upcoming stops.
    
    Returns a list of `Prediction` objects.
    """
    def pt_to_time(pt):
        pt = pt.lower()
        if 'approaching' == pt:
            return True
        elif 'less than' in pt:
            # Less than 2 minutes? ehhh, 1 minute
            return timedelta(minutes=1)
        elif 'min' in pt:
            # "2 MIN" -> ("2", "MIN") -> 2
            minutes = int(pt.split(' '))[0]
            return timedelta(minutes=minutes)
        else:
            raise ValueError("Unsupported ETA %s." % pt)
    
    parser = grabxml(API_BUS % busid)
    if parser.find('pr'):
        for prediction in parser.findall('pr'):
            eta = pt_to_time(prediction.find('pt'))
            stop = prediction.find('stop')
    else:
        raise NoBusPrediction()    
        
        