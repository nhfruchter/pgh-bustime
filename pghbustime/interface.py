import requests
import xmltodict
from repoze.lru import LRUCache, lru_cache

from utils import *

class BustimeError(Exception): pass
class NoPredictionsError(BustimeError): pass
class BustimeWarning(Exception): pass

class BustimeAPI(object):
    """
    A `requests` wrapper around the Port Authority's bustime API with
    some basic error handling and some useful conversions (like an
    option to convert all responses from JSON to XML.)
    
    This attempts to stay relatively close to the actual API's format with
    a few post-processing liberties taken to make things more Python friendly.
    
    Requires: `api_key`

    Optional: `locale` (defaults to en_US)
              `_format` (defaults to `json`, can be `xml`),
              `tmres` (time resolution, defaults to `s`)
              `cache` (cache non-dynamic information, defaults to False;
                       currently caches stops, routes)

    Implements: `bulletins`, `geopatterns`, `predictions`, `route_directions`, 
                `routes`, `stops`, `systemtime`, `vehicles 
    
    If you have an API key:
    >>> bus = PAACBustime(my_api_key)
    
    Official API documentation can be found at the Port Authority site:
    http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=documentation.jsp
    """
    
    __api_version__ = 'v1'
    
    ENDPOINTS = dict(
        SYSTIME = "http://realtime.portauthority.org/bustime/api/v1/gettime",
        VEHICLES = "http://realtime.portauthority.org/bustime/api/v1/getvehicles",
        ROUTES = "http://realtime.portauthority.org/bustime/api/v1/getroutes",
        R_DIRECTIONS = "http://realtime.portauthority.org/bustime/api/v1/getdirections",
        STOPS = "http://realtime.portauthority.org/bustime/api/v1/getstops",
        R_GEO = "http://realtime.portauthority.org/bustime/api/v1/getpatterns",
        PREDICTION = "http://realtime.portauthority.org/bustime/api/v1/getpredictions",
        BULLETINS = "http://realtime.portauthority.org/bustime/api/v1/getservicebulletins"
    )
    
    RESPONSE_TOKEN = "bustime-response"
    ERROR_TOKEN = "error"
    STRPTIME = "%Y%m%d %H:%M:%S"
    
    def __init__(self, apikey, locale="en_US", _format="json", tmres="s"):
        self.key = apikey
        self.format = _format
        self.args = dict(
            localestring = locale,
            tmres = tmres
        )
            
    def endpoint(self, endpt, argdict=None):
        """
        Construct API endpoint URLs using instance options in `self.args` 
        and local arguments passed to the function as a dictionary `argdict`.
        
        >>> api = BustimeAPI("BOGUSAPIKEY")
        >>> api.endpoint('VEHICLES') 
        'http://realtime.portauthority.org/bustime/api/v1/getvehicles?key=BOGUSAPIKEY&tmres=s&localestring=en_US'
        >>> api.endpoint('PREDICTION', dict(stpid=4123, rt="61C"))
        'http://realtime.portauthority.org/bustime/api/v1/getpredictions?key=BOGUSAPIKEY&tmres=s&localestring=en_US&format=json&rt=61C&stpid=4123'
        """
        
        instanceargs = "{}&{}".format(queryjoin(key=self.key), queryjoin(self.args))
        if argdict:
            localargs = queryjoin(argdict)
            querystring = "{}&{}".format(instanceargs, localargs)
        else:    
            querystring = instanceargs
        return "{}?{}".format(self.ENDPOINTS[endpt], querystring)
        
    def response(self, url):
        """Grab an API response."""
        
        resp = requests.get(url).content
        return self.parseresponse(resp)        
                        
    def errorhandle(self, resp):            
        """Parse API error responses and raise appropriate exceptions."""
        if self.format == 'json':
            parsed = xmltodict.parse(resp)
            errors = parsed[self.RESPONSE_TOKEN][self.ERROR_TOKEN]
            # Create list of errors if more than one error response is given
            if type(errors) is list and len(errors) > 1:
                messages = ", ".join([" ".join(["{}: {}".format(k,v) for k, v in e.items()]) for e in errors])
            else:
                messages = " ".join(["{}: {}".format(k,v) for k, v in errors.items()])    
        elif self.format == 'xml':
            import xml.etree.ElementTree as ET
            errors = ET.fromstring(resp).findall(self.ERROR_TOKEN)
            messages = ", ".join(err.find('msg').text for err in errors)
        else:
            raise ValueError("Invalid API response format specified: {}." % self.format)        
        
        raise BustimeError("API returned: {}".format(messages))            
                
    def parseresponse(self, resp):
        """Parse an API response."""
        
        if self.RESPONSE_TOKEN not in resp:
            raise BustimeError("The Bustime API returned an invalid response: {}".format(resp))
        elif self.ERROR_TOKEN in resp:
            return self.errorhandle(resp)
        else:
            if self.format == 'json':
                return xmltodict.parse(resp)[self.RESPONSE_TOKEN]
            elif self.format == 'xml':
                return resp
        
    
    def systemtime(self):
        """
        Get the API's official time (local, eastern).
        
        Arguments: none.
        
        Response:
            `tm`: "Date and time is represented in the following format: YYYYMMDD HH:MM:SS."
            
        http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=time.jsp    
        
        """
        return self.response(self.endpoint('SYSTIME'))
        
    def vehicles(self, vid=None, rt=None):
        """
        Get busses by route or by vehicle ID.
        
        Arguments: either
            `vid`: "Set of one or more vehicle IDs whose location should be returned." 
                   Maximum of 10 `vid`s, either in a comma-separated list or an iterable.

            `rt`: "Set of one or more route designators for which matching vehicles should be returned."
                  Maximum of 10 routes, either in a comma-separated list or an iterable.
                  
        Response:
            `vehicle`: (vehicle container) contains list of
                `vid`: bus #
                `tmstmp`: local date/time of vehicle update
                `lat`, `lon`: position
                `hdg`: vehicle heading (e.g., 0: north, 180: south)
                `pid`: pattern ID of current trip (see `self.geopatterns`)
                `pdist`: distance into trip
                `rt`: route (e.g, 88)
                `des`: bus destinations (e.g., "Penn to Bakery Square")
                `dly` (optional): True if bus is delayed
                `spd`: speed in mph
                `zone`: current zone (usually `None` here)
                `tablockid`, `tatripid`: unsure, seems internal?
                
        http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=vehicles.jsp
        """
        
        if vid and rt:
            raise ValueError("The `vid` and `route` parameters cannot be specified simultaneously.")
        if not (vid or rt):
            raise ValueError("You must specify either the `vid` or `rt` parameter.")

        # Turn list into comma separated string
        if listlike(rt): rt = ",".join( map(str, rt) )
        if listlike(vid): vid = ",".join( map(str, vid) )

        url = self.endpoint('VEHICLES', dict(vid=vid, rt=rt))        
        return self.response(url)
        
    @lru_cache(100)
    def routes(self):
        """
        Return a list of routes currently tracked by the API.
        
        Arguments: none

        Response:
            `route`: (route container) contains list of
                `rt`: route designator (e.g, P1, 88)
                `rtnm`: route name (e.g. EAST BUSWAY-ALL STOPS, PENN)
                `rtclr`: color of route used in map display (e.g. #9900ff),
                         usually unimportant                 
                         
        http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=routes.jsp
        """
        return self.response(self.endpoint('ROUTES'))
        
    @lru_cache(100)
    def route_directions(self, rt):
        """
        Return a list of directions for a route.
        
        The directions seem to always be INBOUND and OUTBOUND for the busses
        currently, where INBOUND is towards downtown and OUTBOUND is away from
        downtown. (No idea if this is going to change.)
        
        Arguments:
            `rt`: route designator
        
        Response:
            list of `dir`: directions served (e.g., INBOUND, OUTBOUND)    
            
        http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=routeDirections.jsp    
        """
        url = self.endpoint('R_DIRECTIONS', dict(rt=rt))
        return self.response(url)

    @lru_cache(1024)
    def stops(self, rt, direction):
        """
        Return a list of stops for a particular route.
        
        Arguments:
            `rt`: route designator
            `dir`: route direction (INBOUND, OUTBOUND)
        
        Response:
            `stop`: (stop container) contains list of 
                `stpid`: unique ID number for bus stop
                `stpnm`: stop name (what shows up on the display in the bus,
                         e.g., "Forbes and Murray")
                `lat`, `lng`: location of stop
                
        http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=stops.jsp        
        """
        url = self.endpoint('STOPS', dict(rt=rt, dir=direction))
        return self.response(url)
    
    def geopatterns(self, rt=None, pid=None):
        """
        Returns a set of geographic points that make up a particular routing
        ('pattern', in API terminology) for a bus route. A bus route can have
        more than one routing.
        
        Arguments: either
            `rt`: route designator
            or
            `pid`: comma-separated list or an iterable of pattern IDs (max 10)
            
        Response:
            `ptr`: (pattern container) contains list of
                `pid`: pattern ID
                `ln`: length of pattern in feet
                `rtdir`: route direction (see `self.route_directions`)
                
                `pt`: geo points, contains list of
                    `seq`: position of point in pattern
                    `typ`: 'S' = stop, 'W' = waypoint

                    -> if `typ` is a stop, will contain:
                    `stpid`, `stpnm`, `pdist` (see `self.stops`)
                    
                    `lat`, `lon`: position of point
                    
        http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=patterns.jsp   
        """
        if rt and pid:
            raise ValueError("The `rt` and `pid` parameters cannot be specified simultaneously.")
        if not (rt or pid):
            ValueError("You must specify either the `rt` or `pid` parameter.")

        if listlike(pid): pid = ",".join(pid)
        
        url = self.endpoint("R_GEO", dict(rt=rt, pid=pid))            
        
        return self._lru_geopatterns(url)    
    
    @lru_cache(1024)
    def _lru_geopatterns(self, url):
        # @lru_cache doesn't support kwargs so this is a bit of a workaround...
        return self.response(url)    
        
    def predictions(self, stpid="", rt="", vid="", maxpredictions=""):
        """
        Retrieve predictions for 1+ stops or 1+ vehicles.
        
        Arguments:
            `stpid`: unique ID number for bus stop (single or comma-seperated list or iterable)
            or
            `vid`: vehicle ID number (single or comma-seperated list or iterable)
            or
            `stpid` and `rt`
            
            `maxpredictions` (optional): limit number of predictions returned

        Response:
            `prd`: (prediction container) contains list of
                `tmstp`: when prediction was generated
                `typ`: prediction type ('A' = arrival, 'D' = departure)
                `stpid`: stop ID for prediction
                `stpnm`: stop name for prediction
                `vid`: vehicle ID for prediction
                `dstp`: vehicle distance to stop (feet)
                `rt`: bus route
                `des`: bus destination
                `prdtm`: ETA/ETD
                `dly`: True if bus delayed
                `tablockid`, `tatripid`, `zone`: internal, see `self.vehicles`
                
        http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=predictions.jsp    
        """
        
        if (stpid and vid) or (rt and vid):
            raise ValueError("These parameters cannot be specified simultaneously.")
        elif not (stpid or rt or vid):
            raise ValueError("You must specify a parameter.")   
        
        if listlike(stpid): stpid = ",".join(stpid)
        if listlike(rt): rt = ",".join(rt)
        if listlike(vid): vid = ",".join(vid)
                 
        if stpid or (rt and stpid) or vid:
            url = self.endpoint('PREDICTION', dict(rt=rt, stpid=stpid, vid=vid, top=maxpredictions))
            return self.response(url)
            
    def bulletins(self, rt="", rtdir="", stpid=""):
        """
        Return list of service alerts ('bulletins') for a route or stop.
        
        Arguments:
            `rt`: route designator
            or
            `stpid`: bus stop number
            or (`rt` and `rtdir`) or (`rt` and `rtdir` and `stpid`)
        
        Response:
             `sb`: (bulletin container) contains list of
                 `nm`: bulletin name/ID
                 `sbj`: bulletin subject
                 `dtl`: full text and/or
                 `brf`: short text
                 `prty`: priority (high, medium, low) 
                 `srvc`: (routes bulletin applies to) contains list of 
                     `rt`: route designator
                     `rtdir`: route direction
                     `stpid`: bus stop ID number
                     `stpnm`: bus stop name
        
        http://realtime.portauthority.org/bustime/apidoc/v1/main.jsp?section=serviceBulletins.jsp
        """
        
        if not (rt or stpid) or (rtdir and not (rt or stpid)):
            raise ValueError("You must specify a parameter.")   

        if listlike(stpid): stpid = ",".join(stpid)
        if listlike(rt): rt = ",".join(rt)
        
        url = self.endpoint('BULLETINS', dict(rt=rt, rtdir=rtdir, stpid=stpid))    
        return self.response(url)
        
        