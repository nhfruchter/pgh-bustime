"""Some utility functions and other stuff."""

class CachedFunction(object):
    """Generate an LRU cached function given a cache object."""
    
    def __init__(self, cache):
        self.cache = cache

    def __call__(self, f):
        cache = self.cache
        marker = _MARKER
        def lru_cached(*arg):
            val = cache.get(arg, marker)
            if val is marker:
                val = f(*arg)
                cache.put(arg, val)
            return val
        lru_cached.__module__ = f.__module__
        lru_cached.__name__ = f.__name__
        lru_cached.__doc__ = f.__doc__
        return lru_cached
        
def queryjoin(argdict=dict(), **kwargs):
    """Turn a dictionary into a querystring for a URL.
    
    >>> args = dict(a=1, b=2, c="foo")
    >>> queryjoin(args)
    "a=1&b=2&c=foo"
    """
    if kwargs: argdict.update(kwargs)
    
    if issubclass(type(argdict), dict):                    
        args = ["{}={}".format(k, v) for k, v in argdict.items() if v != None]
    return "&".join(args)
    
def listlike(obj):
    """Is an object iterable like a list (and not a string)?"""
    
    return hasattr(obj, "__iter__") \
    and not issubclass(type(obj), str)\
    and not issubclass(type(obj), unicode)

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