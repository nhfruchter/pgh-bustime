class Bus(object):
    pass

class Route(object):
    pass
    
class Stop(object):
    pass
    
class Prediction(object):
    pass

class PAACBustime(object):
    API_VEHICLES = "http://realtime.portauthority.org/bustime/api/v1/getvehicles"
    API_ROUTES = "http://realtime.portauthority.org/bustime/api/v1/getroutes"
    API_ROUTES_DIRS = "http://realtime.portauthority.org/bustime/api/v1/getdirections"
    API_STOPS = "http://realtime.portauthority.org/bustime/api/v1/getstops"
    API_ROUTE_GEO = "http://realtime.portauthority.org/bustime/api/v1/getpatterns"
    API_PREDICTION = "http://realtime.portauthority.org/bustime/api/v1/getpredictions"
    
    def __init__(self, apikey, locale="en_US", format="json", tmres="s"):
        self.apikey = apikey
        self.locale = locale
        self.format = json
        self.tmres = tmres
        
    