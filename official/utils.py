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
    if kwargs:
        argdict.update(kwargs)
    if issubclass(type(argdict), dict):
        args = ["{}={}".format(k, v) for k, v in argdict.items()]
    return "&".join(args)
    
def listlike(obj):
    """Is an object iterable like a list (and not a string)?"""
    
    return hasattr(obj, "__iter__") \
    and not issubclass(type(obj), str)\
    and not issubclass(type(obj), unicode)