from datetime import datetime, timedelta
from repoze.lru import lru_cache
from collections import namedtuple 

def patterntogeojson(pattern):
    from geojson import Point, Feature, FeatureCollection
    
    """
    Turns an an API response of a pattern into a GeoJSON FeatureCollection.
    Takes a dict that contains at least `pid`, `ln`, `rtdir`, and `pt`.
    
    >>> api_response = {'ln': '123.45', 'pid': '1', 'pt': [], 'rtdir': 'OUTBOUND'}
    >>> pt1 = {'lat': '40.449', 'lon': '-79.983', 'seq': '1', 'typ': 'W'}
    >>> pt2 = {'stpid': '1', 'seq': '2', 'stpnm': '3142 Test Ave FS', 'lon': '-79.984', 'pdist': '42.4', 'lat': '40.450', 'typ': 'S'}
    >>> api_response['pt'] = [pt1, pt2]
    >>> patterntogeojson(api_response) # doctest: +ELLIPSIS
    {"features": [{"geometry": {"coordinates": ... "name": "3142 Test Ave FS", "type": "stop"}, "type": "Feature"}], "type": "FeatureCollection"}
    """ 
    # Base properties for the pattern
    properties = dict(
        pid = pattern['pid'],
        length = pattern['ln'],
        direction = pattern['rtdir']
    )
    
    pattern_features = []
    
    for point in pattern['pt']:
        # Base properties for each point
        pointprops = dict(
            i = int(point.get('seq')),
            type = "waypoint" if point.get('typ') == 'W' else "stop"
        )
        location = (float(point.get('lon')), float(point.get('lat')))
        # If it's a stop, add stop information
        if pointprops['type'] == 'stop':
            stop = dict(
                id = int(point.get('stpid')),
                name = point.get('stpnm'),
                dist_into_route = float(point.get('pdist'))
            )
            pointprops.update(stop)
        # Create a Feature to encapsulate the point and properties    
        pattern_features.append( Feature(geometry=Point(location), properties=pointprops ) )
    
    return FeatureCollection(pattern_features)

class Bus(object):
    @classmethod
    def fromapi(_class, api, apiresponse):
        """
        Return a Bus object from an API response dict.
        """

        return _class(
            api = api,
            vid = bus['vid'],
            timeupdated = datetime.strptime(bus['tmstp'], api.STRPTIME),
            lat = bus['lat'],
            lng = bus['lng'],
            heading = bus['hdg'],
            pid = bus['pid'],
            dist_into_route = bus['pdist'],
            route = bus['rt'],
            destination = bus['des'],
            speed = bus['spd'],
            delay = bus.get('dly') or False
        )             
    
    def __init__(self, api, vid, timeupdated, lat, lng, heading, pid, intotrip, route, destination, speed, delay=False):
        self.api = api
        self.vid = vid
        self.timeupdated = timeupdated
        self.location = (lat, lng)
        self.patternid = pid
        self.dist_in_trip = intotrip
        self.route = route
        self.destination = destination
        self.speed = speed
        self.delayed = delay
        
    def __str__(self):
        return "<Bus #{} on {} {}> - at {} as of {}".format(self.vid, self.route, self.destination, self.location, self.timeupdated)
        
    def __repr__(self):
        return self.__str__()
    
    def update(self):
        """Update this bus by creating a new one and transplanting dictionaries."""
        vehicle = self.api.vehicles(vid=self.vid)['vehicle']
        self.__dict__ = self.fromapi(vehicle).__dict__
    
    @property
    def pattern(self):
        return self.api.geopatterns(pid=self.patternid)
    
    @property
    @lru_cache(10, timeout=15)
    def predictions(self):
        """Generator that yields prediction objects from an API response."""
        for prediction in self.api.predictions(vid=self.vid)['prd']:
            yield Prediction.fromapi(prediction)
                
    @property
    def next_stop(self):
        """Return the next stop for this bus."""
        p = self.api.predictions(vid=self.vid)['prd']
        return Prediction.fromapi(p[0])
    
        
class Route(object):
    @classmethod
    def fromapi(_class, api, apiresponse):
        return _class(api, apiresponse['rt'], apiresponse['rtnm'])
        
    def __init__(self, api, number, name):
        self.api = api
        self.number = number
        self.name = name
        self.stops = {}
        
    def __str__(self):
        return "{} {}".format(self.number, self.name)
    
    def __repr__(self):
        classname = self.__class__.__name__
        return "{}({},{})".format(classname, self.name, self.number)

    @property
    @lru_cache(2, timeout=60*60*2)
    def bulletins(self):
        for b in self.api.bulletins(rt=self.number)['sb']:
            yield Bulletin.fromapi(b)
    
    @property
    def patterns(self):
        return self.api.geopatterns(rt=self.number)
    
    @property
    def busses(self):
        # TODO turn into Bus objects
        yield self.api.vehicles(rt=self.number)
        
    @property
    def directions(self):
        if not self._directions:
            self._directions = self.api.route_directions(self.number)['dir']
        return self._directions    
        
    @property    
    def inbound_stops(self):
        try:
            return self._stops['inbound']
        except:    
            inboundstops = self.api.stops(self.number, "INBOUND")['stop']
            self._stops['inbound'] = [Stop.fromapi(stop) for stop in inboundstops]
            return self._stops['inbound']
        
    @property    
    def outbound_stops(self):
        try:
            return self._stops['outbound']
        except:    
            outboundstops = self.api.stops(self.number, "OUTBOUND")['stop']
            self._stops['outbound'] = [Stop.fromapi(stop) for stop in outboundstops]
            return self._stops['outbound']
            
    def find_stop(self, query, direction=""):
        """
        Search the list of stops, optionally in a direction (inbound or outbound),
        for the term passed to the function. Case insensitive, searches both the
        stop name and ID. Yields a generator.
        
        Defaults to both directions.
        """
        _directions = ["inbound", "outbound", ""]
        direction = direction.lower()
        if direction == "inbound":
            stops = self.inbound_stops
        elif direction == "outbound":
            stops = self.outbound_stops
        else:
            stops = self.inbound_stops + self.outbound_stops
                   
        for stop in stops:
            q = str(query).lower()
            if q in stop.name.lower() or q in str(stop.id).lower():
                yield q
        
class Stop(object):
    """Represents a single stop."""
    @classmethod
    def fromapi(_class, api, apiresponse):
        location = (apiresponse['lat'], apiresponse['lon'])
        stpid = apiresponse['stpid']
        # There might not be names occasionally
        name = apiresponse.get('stpnm') 
        return _class(stpid, name, location)
    
    def __init__(self, api, _id, name, location):
        self.api = api
        self.id = _id
        self.name = name
        self.location = location
        
    def __str__(self):
        name = "(Unnamed)" or self.name
        return "<Stop #{} {} at {}>".format(self.id, name, self.location)
        
    def __repr__(self):
        classname = self.__class__.__name__
        return "{}({},{},{})".format(classname, self.id, self.name, self.location)
    
    def predictions(self, route=''):
        """
        Yields predicted bus ETAs for this stop.  You can specify a 
        route identifier for ETAs specific to one route, or leave `route`
        blank (done by default) to get information on all arriving busses.
        """   
        for prediction in self.api.predictions(stpid=self.id, rt=rt)['prd']:
            yield Prediction.fromapi(prediction)
        
    @property
    @lru_cache(2, timeout=60*60*2)
    def bulletins(self):
        for b in self.api.bulletins(stpid=self.id)['sb']:
            yield Bulletin.fromapi(b)
        
class Prediction(object):
    pstop = namedtuple("predicted_stop", ['id', 'name', 'feet_to'])
    
    @classmethod
    def fromapi(_class, api, apiresponse):
        generated_time = datetime.strptime(apiresponse['tmstp'], api.STRPTIME)
        arrival = True if apiresponse['typ'] == 'A' else False
        bus = apiresponse['vid']
        stop = _class.pstop(apiresponse['stpid'], apiresonse['stpnm'],  apiresponse['dstp'])
        route = apiresponse['rt']
        destination = apiresponse['des']
        et = datetime.strptime(apiresponse['prdtm'], api.STRPTIME)
        delayed = bool(apiresponse.get('dly'))
        
        return _class(api, et, arrival, delayed, generated_time, stop, route, destination, bus)
        
    def __init__(self, api, eta, is_arrival, delayed, generated, stop, route, destination, bus):
        self.api = api
        self.eta = eta
        self.is_arrival = is_arrival
        self.delayed = delayed
    
        self.generated = generated
    
        self._stop = stop
        self._route, self.destination = route, destination
        self._vid = bus
        
    @property
    def bus(self):
        return Bus.fromapi(self.api.vehicles(vid=self._vid)['vehicles'])
        
    @property
    def route(self):
        rtnm = self.destination.split(" to ")[0]
        return Route(self.api, self.route, rtnm)
        
    @property
    def stop(self):
        return Stop(self.api, self._stop.id, stop._stop.name, (None, None))
        
    @property
    def dist_to_stop(self):
        return self._stop.feet_to    
        
    
class Bulletin(object):    
    """
    A service bulletin, usually representing a detour or other type of
    route change.
    """
    affected_service = namedtuple('affected_service', ['type', 'id', 'name'])
    
    @classmethod 
    def fromapi(_class, apiresponse):
        """Create a bulletin object from an API response (dict), containing `sbj`, etc."""
        
        # Extract details from dict
        _id = "n/a" or apiresponse.get("nm")
        subject = apiresponse.get("sbj")
        text = apiresponse.get('dtl') + "\n" + apiresponse.get('brf')
        priority = "n/a" or apiresponse.get('prty')
        for_stops, for_routes = [], []
        svc = apiresponse.get('srvc')
        
        # Create list of affected routes/stops, if there are any
        if svc:
            has_stop = 'stpid' in svc or 'stpnm' in svc
            has_rt = 'rt' in svc or 'rtdir' in svc
            
            if has_stop: 
                aff = _class.affected_service('stop', svc.get('stpid'), svc.get('stpnm'))
                for_stops.append(aff)
            if has_rt:
                aff = _class.affected_service('route', svc.get('rt'), svc.get('rtdir'))
                for_routes.append(aff)

        return _class(_id, subject, text, priority, for_stops, for_routes)
        
    def __init__(self, _id, subject, text, priority, for_stops=None, for_routes=None):
        self.id = _id
        self.subject = subject
        self.body = text
        self.priority = priority
        self._stops = for_stops or []
        self._routes = for_routes or []
        
    def __str__(self):
        formatted = "Bulletin #{}\n\nSubject: {}\nPriority: {}\n\n{}\n\nValid for stops: {}\nValid for routes: {}"
        return formatted.format(self.id, self.subject, self.priority, self.body, self._stops, self._routes)
        
    @property
    def valid_for(self):
        return dict(
            stops=self._stops,
            routes=self._routes
        )