import unittest
import pghbustime as p
import pickle
from collections import OrderedDict

class TestAPI(unittest.TestCase):    
    def setUp(self):
        self.api = p.BustimeAPI("BOGUSAPIKEY")
        
class TestEndpoint(TestAPI):
    def test_vehicle(self):
        url = "http://realtime.portauthority.org/bustime/api/v1/getvehicles?key=BOGUSAPIKEY&tmres=s&localestring=en_US"
        self.assertEqual( self.api.endpoint('VEHICLES'), url )
    
    def test_pdict(self):
        url = 'http://realtime.portauthority.org/bustime/api/v1/getpredictions?key=BOGUSAPIKEY&tmres=s&localestring=en_US&rt=28X&stpid=4123'
        generated = self.api.endpoint('PREDICTION', dict(stpid=4123, rt='28X') )
        self.assertEqual( generated, url )
        
class TestRespParser(TestAPI):
    def setUp(self):
        self.api = p.BustimeAPI("BOGUSAPIKEY")
        self.validparse = OrderedDict([(u'route', [OrderedDict([(u'rt', u'13'), (u'rtnm', u'BELLEVUE'), (u'rtclr', u'#ff6666')]), OrderedDict([(u'rt', u'28X'), (u'rtnm', u'AIRPORT FLYER'), (u'rtclr', u'#b22222')])])])
        self.validxml = """
        <?xml version="1.0"?>
        <bustime-response>
        	<route>
        		<rt>13</rt>
        		<rtnm>BELLEVUE</rtnm>
        		<rtclr>#ff6666</rtclr>
        	</route>		

        	<route>
        		<rt>28X</rt>
        		<rtnm>AIRPORT FLYER</rtnm>
        		<rtclr>#b22222</rtclr>
        	</route>		

        	</bustime-response>""".strip()
    
        self.errxml = '<?xml version="1.0"?>\n<bustime-response><error><msg>Invalid API access key supplied</msg></error></bustime-response>'

    def test_correct_rt(self):
        self.assertEqual( self.validparse, self.api.parseresponse(self.validxml) )
        
    def test_errhandle(self):
        try:
            self.api.errorhandle(self.errxml)
            passed = False
        except p.BustimeError:
            passed = True
        
        self.assertEquals(passed, True)    
        
    def test_errhandoff(self):
        try:
            self.api.parseresponse(self.errxml)
            passed = False
        except p.BustimeError:
            passed = True    
            
        self.assertEquals(passed, True)    
        
    def test_invalidresp(self):
        try:
            self.api.parseresponse("thisshouldbreak")
            passed = False
        except p.BustimeError: 
            passed = True
        
    def test_incorrect_err(self):
        try:
            r = self.api.errorhandle(self.validxml)
        except KeyError:
            r = False
        
        self.assertEquals(r, False)
        
    def test_vid_args(self):
        try:
            x = self.api.vehicles()
            passed = False
        except ValueError:
            passedA = True
            
        try:
            y = self.api.vehicles(vid=123, rt=54)
            passed = False
        except ValueError:
            passedB = True
            
        self.assertEquals(passedA, True)        
        self.assertEquals(passedB, True)        
        
class TestUtils(unittest.TestCase):        
    def test_queryjoin(self):
        args = dict(a=1, b=2, c="foo")
        self.assertEquals( p.utils.queryjoin(args), 'a=1&c=foo&b=2')
                
    def test_listlike(self):
        self.assertEquals(p.utils.listlike([]), True)
        self.assertEquals(p.utils.listlike(()), True)
        self.assertEquals(p.utils.listlike((i for i in [])), True)
        self.assertEquals(p.utils.listlike("hello"), False)
        
    def test_p2geojson(self):
        api_response = {'ln': '123.45', 'pid': '1', 'pt': [], 'rtdir': 'OUTBOUND'}
        pt1 = {'lat': '40.449', 'lon': '-79.983', 'seq': '1', 'typ': 'W'}
        pt2 = {'stpid': '1', 'seq': '2', 'stpnm': '3142 Test Ave FS', 'lon': '-79.984', 'pdist': '42.4', 'lat': '40.450', 'typ': 'S'}
        api_response['pt'] = [pt1, pt2]
        geojson = p.utils.patterntogeojson(api_response)
        
        correctpkl = "ccopy_reg\n_reconstructor\np0\n(cgeojson.feature\nFeatureCollection\np1\nc__builtin__\ndict\np2\n(dp3\nS'type'\np4\nS'FeatureCollection'\np5\nsS'features'\np6\n(lp7\ng0\n(cgeojson.feature\nFeature\np8\ng2\n(dp9\nS'geometry'\np10\ng0\n(cgeojson.geometry\nPoint\np11\ng2\n(dp12\ng4\nS'Point'\np13\nsS'coordinates'\np14\n(F-79.983\nF40.449\ntp15\nstp16\nRp17\nsg4\nS'Feature'\np18\nsS'id'\np19\nNsS'properties'\np20\n(dp21\nS'i'\np22\nI1\nsg4\nS'waypoint'\np23\nsstp24\nRp25\nag0\n(g8\ng2\n(dp26\ng10\ng0\n(g11\ng2\n(dp27\ng4\ng13\nsg14\n(F-79.984\nF40.45\ntp28\nstp29\nRp30\nsg4\ng18\nsg19\nNsg20\n(dp31\ng22\nI2\nsS'dist_into_route'\np32\nF42.4\nsg4\nS'stop'\np33\nsS'name'\np34\nS'3142 Test Ave FS'\np35\nsg19\nI1\nsstp36\nRp37\nastp38\nRp39\n."
        self.assertEquals(geojson, pickle.loads(correctpkl))
        
class TestObjects(TestAPI):        
    def test_vehicles(self):
        bus5666 = OrderedDict([(u'vid', u'5666'), (u'tmstmp', u'20140925 22:46:33'), (u'lat', u'40.44886169433594'), (u'lon', u'-80.16286682128906'), (u'hdg', u'164'), (u'pid', u'2250'), (u'rt', u'28X'), (u'des', u'Oakland'), (u'pdist', u'49113'), (u'spd', u'16'), (u'tablockid', u'028X-022'), (u'tatripid', u'52562'), (u'zone', None)])
        bobj = p.Bus.fromapi(self.api, bus5666)
        result = "<Bus #5666 on 28X Oakland> - at (40.44886169433594, -80.16286682128906) as of 2014-09-25 22:46:33-04:00"
        self.assertEquals(str(bobj), result)
        self.assertEquals(bobj.api, self.api)
        self.assertEquals(bobj.delayed, False)
        self.assertEquals(bobj.dist_in_trip, "49113")
        self.assertEquals(bobj.speed, "16")
        self.assertEquals(bobj.patternid, "2250")
        
if __name__ == '__main__':
    unittest.main()