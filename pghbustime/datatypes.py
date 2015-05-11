from datetime import datetime, timedelta
from collections import namedtuple 
from pytz import timezone

from utils import listlike
from interface import BustimeError, BustimeWarning

class Bus(object):
    """Represents an individual vehicle on a route with a location."""
    
    @classmethod

    def get(_class, api, vid):
        """
        Return a Bus object for a certain vehicle ID `vid` using API
        instance `api`.
        """
        busses = api.vehicles(vid=vid)['vehicle']   
        return _class.fromapi(api, api.vehicles(vid=vid)['vehicle'])
        
    @classmethod
    def fromapi(_class, api, apiresponse):
        """
        Return a Bus object from an API response dict.
        """
        bus = apiresponse
        return _class(
            api = api,
            vid = bus['vid'],
            timeupdated = datetime.strptime(bus['tmstmp'], api.STRPTIME),
            lat = float(bus['lat']),
            lng = float(bus['lon']),
            heading = bus['hdg'],
            pid = bus['pid'],
            intotrip = bus['pdist'],
            route = bus['rt'],
            destination = bus['des'],
            speed = bus['spd'],
            delay = bus.get('dly') or False
        )             

    def __init__(self, api, vid, timeupdated, lat, lng, heading, pid, intotrip, route, destination, speed, delay=False):
        self.api = api
        self.vid = vid
        self.timeupdated = timezone("US/Eastern").localize(timeupdated)
        self.location = (lat, lng)
        self.heading = int(heading)
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
        newbus = self.fromapi(self.api, vehicle)
        self.__dict__ = newbus.__dict__
        del newbus
    
    @property
    def pattern(self):
        return self.api.geopatterns(pid=self.patternid)
    
    @property
    def predictions(self):
        """Generator that yields prediction objects from an API response."""
        for prediction in self.api.predictions(vid=self.vid)['prd']:
            pobj = Prediction.fromapi(self.api, prediction)
            pobj._busobj = self
            yield pobj
                
    @property
    def next_stop(self):
        """Return the next stop for this bus."""
        p = self.api.predictions(vid=self.vid)['prd']
        pobj = Prediction.fromapi(self.api, p[0])
        pobj._busobj = self
        return pobj
        
class OfflineBus(Bus): 
    """Sometimes, busses can be still present in the tracking system but not be
    reporting live data back, which causes the API to fail. This object is a
    representation for that case so the prediction function does not throw an
    exception."""       
    
    def __init__(self, vid):
        self.vid = vid
        
    def __str__(self):
        return "<Bus #{}: NO DATA [Location Currently Offline]>".format(self.vid)
        
        
class Route(object):
    """Represents a certain bus route (e.g. P1). Also contains a list of all the valid routes."""
    all_routes = {} # store list of all routes currently
    
    @classmethod
    def update_list(_class, api, rtdicts):
        allroutes = {}
        for rtdict in rtdicts:
            rtobject = Route.fromapi(api, rtdict)
            allroutes[str(rtobject.number)] = rtobject
        return allroutes
    
    @classmethod
    def get(_class, api, rt):
        """
        Return a Route object for route `rt` using API instance `api`.
        """
             
        if not _class.all_routes:
            _class.all_routes = _class.update_list(api, api.routes()['route'])

        return _class.all_routes[str(rt)]
        
    @classmethod
    def fromapi(_class, api, apiresponse):
        return _class(api, apiresponse['rt'], apiresponse['rtnm'], apiresponse['rtclr'])
        
    def __init__(self, api, number, name, color):
        self.api = api
        self.number = number
        self.name = name
        self.color = color
        self.stops = {}
        
    def __str__(self):
        return "{} {}".format(self.number, self.name)
    
    def __repr__(self):
        classname = self.__class__.__name__
        return "{}({}, {})".format(classname, self.name, self.number)
        
    def __hash__(self):
        return hash(str(self))

    @property
    def bulletins(self):
        apiresponse = self.api.bulletins(rt=self.number)
        if apiresponse:
            for b in apiresponse['sb']:
                yield Bulletin.fromapi(b)
    
    @property 
    def detours(self):
        self._detours = self.api.detournotices(self.number)
        return self._detours
        
    @property
    def patterns(self):
        return self.api.geopatterns(rt=self.number)
    
    @property
    def busses(self):
        apiresp = self.api.vehicles(rt=self.number)['vehicle']
        if type(apiresp) is list:
            for busdict in apiresp:
                busobj = Bus.fromapi(self.api, busdict)
                busobj.route = self
                yield busobj
        else:
                busobj = Bus.fromapi(self.api, apiresp)
                busobj.route = self
                yield busobj
        
    @property
    def directions(self):
        if not hasattr(self, "_directions"):
            self._directions = self.api.route_directions(self.number)['dir']
        return self._directions    
        
    @property    
    def inbound_stops(self):
        try:
            return self.stops['inbound']
        except:    
            inboundstops = self.api.stops(self.number, "INBOUND")['stop']
            self.stops['inbound'] = [StopWithLocation.fromapi(self.api, stop) for stop in inboundstops]
            return self.stops['inbound']
        
    @property    
    def outbound_stops(self):
        try:
            return self.stops['outbound']
        except:    
            outboundstops = self.api.stops(self.number, "OUTBOUND")['stop']
            self.stops['outbound'] = [StopWithLocation.fromapi(self.api, stop) for stop in outboundstops]
            return self.stops['outbound']
            
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
        
        found = []
        for stop in stops:
            q = str(query).lower()
            if q in stop.name.lower() or q in str(stop.id).lower():
                found.append(stop)
        return found
    
class Stop(object):
    """Represents a single stop."""
    
    @classmethod
    def get(_class, api, stpid):
        """
        Returns a Stop object for stop # `stpid` using API instance `api`.
        The API doesn't support looking up information for an individual stop,
        so all stops generated using Stop.get only have stop ID # info attached.
        
        Getting a stop from a Route is the recommended method of finding a specific
        stop (using `find_stop`/`inbound_stop`/`outbound_stop` functions).
        
        >>> Stop.get(1605)
        Stop(1605, "(Unnamed)")
        """
        return _class(api, stpid, "(Unnamed)")
            
    def __init__(self, api, _id, name):
        self.api = api
        self.id = _id
        self.name = name        
        
    def __repr__(self):
        classname = self.__class__.__name__
        return "{}({}, {})".format(classname, self.id, self.name)
        
    def __hash__(self):
        return hash(str(self))
    
    def predictions(self, route=''):
        """
        Yields predicted bus ETAs for this stop.  You can specify a 
        route identifier for ETAs specific to one route, or leave `route`
        blank (done by default) to get information on all arriving busses.
        """   
        apiresponse = self.api.predictions(stpid=self.id, rt=route)['prd']
        if type(apiresponse) is list:        
            for prediction in apiresponse:
                try:
                    pobj = Prediction.fromapi(self.api, prediction)
                    pobj._stopobj = self
                    yield pobj
                except:
                    continue    
        else:
            pobj = Prediction.fromapi(self.api, apiresponse)
            pobj._stopobj = self
            yield pobj
                
    @property
    def bulletins(self):
        apiresponse = self.api.bulletins(stpid=self.id)
        if apiresponse:
            for b in apiresponse['sb']:
                yield Bulletin.fromapi(b)

class StopWithLocation(Stop):      
    """Represents a Stop with an added location parameter."""
    
    def get(self):
        raise NotImplementedError
        
    @classmethod
    def fromapi(_class, api, apiresponse):
        location = (apiresponse['lat'], apiresponse['lon'])
        stpid = apiresponse['stpid']
        # There might not be names occasionally
        name = apiresponse.get('stpnm') 
        return _class(api, stpid, name, location)
        
    def __init__(self, api, _id, name, location):
        super(StopWithLocation, self).__init__(api, _id, name)
        self.location = location
    
    def __str__(self):
        name = self.name or "(Unnamed)" 
        return "<Stop #{} {} at {}>".format(self.id, name, self.location)
    
    def __repr__(self):
        classname = self.__class__.__name__
        return "{}({}, {}, {})".format(classname, self.id, self.name, self.location)            
        
class Prediction(object):
    """Represents an ETA or ETD prediction for a certain Bus and/or Stop."""
    
    pstop = namedtuple("predicted_stop", ['id', 'name', 'feet_to'])

    @classmethod
    def fromapi(_class, api, apiresponse):
        generated_time = datetime.strptime(apiresponse['tmstmp'], api.STRPTIME)
        arrival = True if apiresponse['typ'] == 'A' else False
        bus = apiresponse['vid']
        stop = _class.pstop(apiresponse['stpid'], apiresponse['stpnm'], int(apiresponse['dstp']))
        route = apiresponse['rt']
        direction = apiresponse['rtdir']
        destination = apiresponse['des']
        et = datetime.strptime(apiresponse['prdtm'], api.STRPTIME)
        delayed = bool(apiresponse.get('dly'))
        
        return _class(api, et, arrival, delayed, generated_time, stop, route, destination, bus, direction)
        
    def __init__(self, api, eta, is_arrival, delayed, generated, stop, route, destination, bus, direction):
        self.api = api
        self.eta = timezone("US/Eastern").localize(eta) # Datetime ETA
        self.is_arrival = is_arrival # Is
        self.delayed = delayed
        self.generated = timezone("US/Eastern").localize(generated)
        self._stop = stop
        self.route, self.destination = route, destination
        self.direction = direction
        self._vid = bus

    def __str__(self):
        phrase = "ETA" if self.is_arrival else "ETD"
        return "<Prediction> {}: {} Bus: {} Stop: {}".format(phrase, self.eta, self.bus, self.stop, self.freshness)
    
    def __repr__(self):
        return str(self)
        
    @property
    def bus(self):
        if not hasattr(self, "_busobj"):
            try:
                self._busobj = Bus.fromapi(self.api, self.api.vehicles(vid=self._vid)['vehicle'])
            except BustimeError:
                self._busobj = OfflineBus(self._vid)  
        return self._busobj    
        
    @property
    def stop(self):
        if not hasattr(self, "_stopobj"):
            self._stopobj = Stop(self.api, self._stop.id, self._stop.name)
        return self._stopobj
        
    @property
    def dist_to_stop(self):
        return self._stop.feet_to    
        
    @property
    def freshness(self):
        now = datetime.now(timezone("US/Eastern"))
        change = divmod((now - self.generated).total_seconds(), 60)
        return timedelta(minutes=change[0], seconds=change[1])
        
class Bulletin(object):    
    """
    A service bulletin, usually representing a detour or other type of
    route change.
    """
    affected_service = namedtuple('affected_service', ['type', 'id', 'name'])
    @classmethod
    def get(_class, api, rt=None, rtdir=None, stpid=None):        
        if not (rt or stpid) or (rtdir and not (rt or stpid)):
            raise ValueError("You must specify a parameter.")   

        if listlike(stpid): stpid = ",".join(stpid)
        if listlike(rt): rt = ",".join(rt)
        
        bulletins = api.bulletins(rt=rt, rtdir=rtdir, stpid=stpid)
        
        if bulletins:
            bulletins = bulletins['sb']
            if type(bulletins) is list:
                return [_class.fromapi(b) for b in bulletins]
            else:
                return _class.fromapi(bulletins)        
    
    @classmethod 
    def fromapi(_class, apiresponse):
        """Create a bulletin object from an API response (dict), containing `sbj`, etc."""
        for resp in apiresponse['sb']:
            # Extract details from dict
            _id = "n/a" or resp.get("nm")
            subject = resp.get("sbj")
            text = resp.get('dtl') + "\n" + resp.get('brf')
            priority = "n/a" or resp.get('prty')
            for_stops, for_routes = [], []
            svc = resp.get('srvc')
        
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

            yield _class(_id, subject, text, priority, for_stops, for_routes)
        
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
    
        