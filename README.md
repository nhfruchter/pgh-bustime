# pghbustime

This time, it's official: an interface to Port Authority's official API.

## Yes, you need an API key
Register for an account on the [Port Authority site](http://realtime.portauthority.org/).

## Examples

### Setup
	>>> from pghbustime import *
	>>> mykey = "your_api_key"
	>>> api = BustimeAPI(mykey) # or BustimeAPI(mykey, _format="xml"); defaults to JSON
	
### Using raw API output
If you want just your standard JSON output, just use the API (which is a wrapper around the `requests` module.)

Get info about busses:

    >>> api.vehicles(rt=88)
	OrderedDict([(u'vehicle', [OrderedDict([(u'vid', u'3241'), (u'tmstmp', u'20140815 15:00:18'), (u'lat', u'40.44547070197339')... (u'zone', None)])])])

All stops on the P1 route:

	>>> api.stops("P1", "OUTBOUND")
	 OrderedDict([(u'stop', [OrderedDict([(u'stpid', u'8165'), (u'stpnm', u'East Liberty Station stop A'), (u'lat', u'40.459440916034'...)])])
	 
Next bus at stop 8165 ("East Liberty Station stop A")	 

	>>> api.predictions(stpid=8165, maxprediction=1)
	OrderedDict([(u'prd', OrderedDict([(u'tmstmp', u'20140815 15:06:35'), (u'typ', u'A'), (u'stpnm', u'East Liberty Station stop A'), (u'stpid', u'8165'), 
	(u'vid', u'3241'), (u'dstp', u'955'), (u'rt', u'P1'), (u'rtdir', u'OUTBOUND'), (u'des', u'East Busway to Swissvale'), (u'prdtm', u'20140815 15:06:55'), 
	(u'tablockid', u'P1  -370'), (u'tatripid', u'51924'), (u'zone', None)]))])
	
### A more object-oriented interface
Current location of all busses on route P1:

	>>> p1 = Route.get(api, "P1")
	>>> list(p1.busses)
	[<Bus #3332 on P1 EAST BUSWAY-ALL STOPS East Busway to Swissvale> - at (40.42644660703598, -79.88550100018901) as of 2014-08-15 15:30:46,
	 <Bus #3326 on P1 EAST BUSWAY-ALL STOPS East Busway to Town> - at (40.41942611395144, -79.88638604856006) as of 2014-08-15 15:31:21...
	 <Bus #3210 on P1 EAST BUSWAY-ALL STOPS East Busway to Town> - at (40.44169235229492, -79.99764060974121) as of 2014-08-15 15:31:01]
		 
Info on a particular bus:

	>>> bus3212 = list(p1.busses)[3]		 
	>>> list(bus3212.predictions) # Next stops for the bus
	[<Prediction> ETA: 2014-08-15 15:35:36 Bus: <Bus #3210 on P1 EAST BUSWAY-ALL STOPS East Busway to Swissvale> - at (40.441384724208284, -79.99755750383649) as of 2014-08-15 15:32:39 Stop: Stop(3427, Grant St at Post Office) - Freshness: -1 day, 23:00:06.128954 ago...]
	>>> bus3212.next_stop 
	<Prediction> ETA: 2014-08-15 15:39:59 Bus: <Bus #3210 on P1 EAST BUSWAY-ALL STOPS East Busway to Swissvale> - at (40.441384724208284, -79.99755750383649) as of 2014-08-15 15:32:39 Stop: Stop(5125, Herron Station stop A) - Freshness: 0:01.774215 ago
	>>> bus3212.update() # Update the current position and other info
	
You can chain everything together, too.  Find the next P3 bus at the outbound Negley stop:

	>>> Route.get(api, "P3").find_stop("Negley", "OUTBOUND")[0].predictions().next()
	<Prediction> ETA: 2014-08-15 15:30:08 Bus: <Bus #3217 on P1 East Busway to Swissvale> - at (40.45962446281709, -79.96585441497434) as of 2014-08-15 15:26:13 
	Stop: <Stop #20501 Negley Station stop A at (u'40.456606823343', u'-79.932646291005')> - Freshness: 00:04.936698 ago

### A note on caching
Caching the results of your API queries in an expiring local store of some sort is highly recommended due to the API's somewhat restrictive initial limits. I highly recommend a Python LRU cache module or `memcache`.
	
