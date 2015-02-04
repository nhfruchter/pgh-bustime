"""Some utility functions and other stuff."""

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

def patterntogeojson(pattern, color=False):
    import geojson
    
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
        direction = pattern['rtdir'],
        color = color or ""
    )        
        
    points = [(float(point.get('lon')), float(point.get('lat'))) for point in pattern['pt']]
    
    return geojson.LineString(coordinates=points, properties=properties)