from builtins import str
import unittest
import pghbustime as p
import pickle
from collections import OrderedDict

class TestAPI(unittest.TestCase):    
    def setUp(self):
        self.api = p.BustimeAPI("BOGUSAPIKEY")
        
class TestEndpoint(TestAPI):
    def test_vehicle(self):
        url = "http://realtime.portauthority.org/bustime/api/v3/getvehicles?key=BOGUSAPIKEY&localestring=en_US&rtpidatafeed=Port+Authority+Bus&tmres=s"
        self.assertEqual( self.api.endpoint('VEHICLES'), url )
    
    def test_pdict(self):
        url = 'http://realtime.portauthority.org/bustime/api/v3/getpredictions?key=BOGUSAPIKEY&localestring=en_US&rtpidatafeed=Port+Authority+Bus&tmres=s&rt=28X&stpid=4123'
        generated = self.api.endpoint('PREDICTION', dict(stpid=4123, rt='28X') )
        self.assertEqual( generated, url )
        
class TestRespParser(TestAPI):
    def setUp(self):
        self.api = p.BustimeAPI("BOGUSAPIKEY")
        self.validparse = OrderedDict([(u'route', [OrderedDict([(u'rt', u'13'), (u'rtnm', u'BELLEVUE'), (u'rtclr', u'#ff6666')]), OrderedDict([(u'rt', u'28X'), (u'rtnm', u'AIRPORT FLYER'), (u'rtclr', u'#b22222')])])])
        self.validxml = b"""
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
    
        self.errxml = b'<?xml version="1.0"?>\n<bustime-response><error><msg>Invalid API access key supplied</msg></error></bustime-response>'
        self.mockbulletin = b"""<?xml version="1.0"?>
<bustime-response>
  <sb>
    <sbj>Stop Relocation</sbj>
    <dtl>The Westbound stop located at Madison/Lavergne has been moved...</dtl>
    <brf>Westbound stop located at Madison/Lavergne is at NE corner.</brf>
    <prty>low</prty>
    <srvc>
      <rt>20</rt>
    </srvc>
  </sb>
  <sb>
    <sbj>Stop Relocations/Eliminations</sbj>
    <dtl>Bus stops are being changed to provide faster travel time.</dtl>
    <brf>Bus stops are being changed to provide faster travel time.</brf>
    <prty>low</prty>
    <srvc>
      <stpid>456</stpid>
    </srvc>
  </sb>
</bustime-response>"""

    def test_correct_rt(self):
        self.assertEqual( self.validparse, self.api.parseresponse(self.validxml) )
        
    def test_errhandle(self):
        try:
            self.api.errorhandle(self.errxml)
            passed = False
        except p.BustimeError:
            passed = True
        
        self.assertEqual(passed, True)    
        
    def test_errhandoff(self):
        try:
            self.api.parseresponse(self.errxml)
            passed = False
        except p.BustimeError:
            passed = True    
            
        self.assertEqual(passed, True)    
        
    def test_invalidresp(self):
        try:
            self.api.parseresponse(b"thisshouldbreak")
            passed = False
        except p.BustimeError: 
            passed = True
        
    def test_incorrect_err(self):
        try:
            r = self.api.errorhandle(self.validxml)
        except KeyError:
            r = False
        
        self.assertEqual(r, False)
        
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
            
        self.assertEqual(passedA, True)        
        self.assertEqual(passedB, True)
        
    def test_bulletin(self):
        bulletins = list(p.Bulletin.fromapi(self.api.parseresponse(self.mockbulletin)))
        singleBulletin = bulletins[0]
        
        self.assertEqual(singleBulletin.subject, 'Stop Relocation')
        self.assertEqual(singleBulletin.id, 'n/a')
        self.assertEqual(len(singleBulletin.valid_for['routes']), 1)
        self.assertEqual(singleBulletin.valid_for['routes'][0].id, '20')
        
class TestUtils(unittest.TestCase):        
    def test_queryjoin(self):
        args = dict(a=1, b=2, c="foo")
        self.assertEqual( p.utils.queryjoin(args), 'a=1&b=2&c=foo')
                
    def test_listlike(self):
        self.assertEqual(p.utils.listlike([]), True)
        self.assertEqual(p.utils.listlike(()), True)
        self.assertEqual(p.utils.listlike((i for i in [])), True)
        self.assertEqual(p.utils.listlike("hello"), False)
        
        
class TestObjects(TestAPI):        
    def test_vehicles(self):
        bus5666 = OrderedDict([(u'vid', u'5666'), (u'tmstmp', u'20140925 22:46:33'), (u'lat', u'40.44886169433594'), (u'lon', u'-80.16286682128906'), (u'hdg', u'164'), (u'pid', u'2250'), (u'rt', u'28X'), (u'des', u'Oakland'), (u'pdist', u'49113'), (u'spd', u'16'), (u'tablockid', u'028X-022'), (u'tatripid', u'52562'), (u'zone', None)])
        bobj = p.Bus.fromapi(self.api, bus5666)
        result = "<Bus #5666 on 28X Oakland> - at (40.44886169433594, -80.16286682128906) as of 2014-09-25 22:46:33-04:00"
        self.assertEqual(str(bobj), result)
        self.assertEqual(bobj.api, self.api)
        self.assertEqual(bobj.delayed, False)
        self.assertEqual(bobj.dist_in_trip, "49113")
        self.assertEqual(bobj.speed, "16")
        self.assertEqual(bobj.patternid, "2250")
        
if __name__ == '__main__':
    unittest.main()
