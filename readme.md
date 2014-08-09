# pgh-bustime

A Python interface to the Port Authority's semi-public real time bus data API.

## Undocumented API information
[The Port Authority's realtime tracking site](http://realtime.portauthority.org) uses an undocumented API to grab its information. Luckily, it's public-facing and outputs relatively readable XML files.

Endpoints that I've found:

* `http://realtime.portauthority.org/bustime/map/getBusPredictions.jsp?bus=%s`
	* ETA/"next stop" predictions by vehicle ID.
* `http://realtime.portauthority.org/bustime/map/getBusesForRoute.jsp?route=%s`
	* All busses on a particular route (e.g., P1).
* `http://realtime.portauthority.org/bustime/eta/getStopPredictionsETA.jsp?route=%s&stop=%s`
	* ETA for bus arrivals at a particular stop.  You can filter by route, or get all busses coming to the stop by setting your route to "all".
* `http://realtime.portauthority.org/bustime/map/getStopsForRouteDirection.jsp?route=%s&direction=%s`
	* Get all bus stops on a route going either "INBOUND" or "OUTBOUND"
* `http://realtime.portauthority.org/bustime/map/getStopPredictions.jsp?route=%s&stop=%s`
	* Seems to be the same as `getStopPredictionsETA` except it gives more info on the stop (name, for example).
	* This is just currently used to get stop names. Maybe not the right use.

## Examples

### ETA at a particular bus stop
From the route:

	>>> from portauthority import *
	>>> p1busway = get_route("P1")
	>>> p1busway.stops # List of all stops
	[Stop(8165), ..., Stop(16104)]
	>>> stop = p1busway.find_stop("Negley")[0]
	>>> list(stop.arriving_busses) # Returns a generator
	[<Prediction for route=P1 arriving at Stop #20501 - Negley Station stop A in 0:09:59.999340 - freshness 0>,
	 <Prediction for route=P1 arriving at Stop #20501 - Negley Station stop A in 0:24:59.999296 - freshness 0>]
	>>> stop.update_arrivals()
	>>> list(stop.arriving_busses) 
	[<Prediction for route=P1 arriving at Stop #20501 - Negley Station stop A in 0:05:59.999341 - freshness 0>,
	 <Prediction for route=P1 arriving at Stop #20501 - Negley Station stop A in 0:20:59.999280 - freshness 0>]

Or more directly:
    
    >>> list(next_bus(20501))

### Bus location by route
From the route:

    >>> p1busway.busses
	[<Bus #3328 route='P1 East Busway to Town' - currently @ (40.41524124145508, -79.87883758544922) - freshness 0s>,
	 <Bus #3327 route='P1 East Busway to Swissvale' - currently @ (40.44817176231971, -79.98597541222206) - freshness 0s>,
	 <Bus #3215 route='P1 East Busway to Town' - currently @ (40.45755121263407, -79.93062255342127) - freshness 0s>,
	 <Bus #3323 route='P1 East Busway to Swissvale' - currently @ (40.41540043170635, -79.8795418372521) - freshness 0s>]
	>>> a_bus = p1busway.busses[0]
	>>> a_bus.loc, a_bus.dest, a_bus.outbound
	((40.41524124145508, -79.87883758544922), 'East Busway to Town', False)
	>>> a_bus.next_stops # Usually provides up to 3-4 predictions.
	[<BusPrediction for bus #3323 arriving at Hamnett Station stop C in 0:02:00>,
	 <BusPrediction for bus #3323 arriving at Wilkinsburg Station stop C in 0:04:00>...
	]
	>>> p1busway.update() # Now the object's realtime data has been refreshed

Or more directly:

	>>> list( next_stop(3323) )


