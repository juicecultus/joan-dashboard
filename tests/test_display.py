import os
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageChops
from joan_dashboard import _prepare_device_image, WIDTH, HEIGHT
from screens import shared
from screens.moon_phase import _draw_moon
from screens.family_photo import render_family_photo, _portrait_image, _immich_photo
from io import BytesIO
from screens.trains import _locations, render_trains

class DisplayTests(unittest.TestCase):
    def test_clockwise_mount_preserves_portrait_pixels(self):
        img=Image.new('L',(1200,1600),255)
        ImageDraw.Draw(img).rectangle((30,70,230,390),fill=0)
        with patch.dict(os.environ, {'PORTRAIT_ROTATION':'90'}):
            native=_prepare_device_image(img,(1600,1200))
        self.assertEqual(native.size,(1600,1200))
        self.assertIsNone(ImageChops.difference(img,native.rotate(-90,expand=True)).getbbox())

    def test_resize_does_not_stretch(self):
        img=Image.new('L',(1200,1600),0)
        out=_prepare_device_image(img,(1024,758))
        self.assertEqual(out.size,(1024,758))
        self.assertEqual(out.getpixel((0,0)),255)

    def test_moon_new_full_and_quarters(self):
        for phase, left, right in [(0,0,0),(14.7652944265,255,255),(7.38264721325,0,255),(22.14794163975,255,0)]:
            img=Image.new('L',(220,220),255)
            _draw_moon(ImageDraw.Draw(img),110,110,100,phase)
            self.assertEqual(img.getpixel((60,110)),left)
            self.assertEqual(img.getpixel((160,110)),right)

    def test_empty_fetch_does_not_poison_good_cache(self):
        with patch.object(shared,'_cache',{'test':{'data':['good'],'ts':100}}), patch.object(shared.time,'time',return_value=200):
            self.assertEqual(shared._cache_fetch('test',10,300,lambda:[]),['good'])
            self.assertEqual(shared._cache['test']['ts'],100)
            self.assertIsNone(shared._cache_fetch('test',10,50,lambda:None))

    def test_text_stays_in_box(self):
        for text in ['W'*150,'A moderately long sentence. '*8,'中文測試'*25]:
            img,draw=shared._canvas()
            shared._fit_block(draw,text,(80,100,1040,1000),120)
            bbox=ImageChops.invert(img).getbbox()
            self.assertTrue(bbox and bbox[0]>=80 and bbox[2]<=1120 and bbox[1]>=100 and bbox[3]<=1100,bbox)
        with self.assertRaises(ValueError):
            shared._fit_block(draw,'overflow',(100,100,1400,500))

    def test_missing_photo_directory_is_not_created(self):
        with tempfile.TemporaryDirectory() as d, patch('screens.family_photo.PHOTOS_DIR',d+'/missing'), patch('screens.family_photo.IMMICH_API_KEY',''):
            with self.assertRaises(shared.ScreenUnavailable): render_family_photo()
            self.assertFalse(os.path.exists(d+'/missing'))

    def test_only_portrait_pixels_are_accepted(self):
        for size in [(100,200),(200,100),(100,100)]:
            data=BytesIO(); Image.new('RGB',size,'gray').save(data,format='JPEG')
            self.assertEqual(_portrait_image(data.getvalue()) is not None, size[1]>size[0])
        data=BytesIO(); img=Image.new('RGB',(200,100),'gray')
        exif=img.getexif(); exif[274]=6
        img.save(data,format='JPEG',exif=exif)
        self.assertEqual(_portrait_image(data.getvalue()).size,(100,200))

    def test_immich_skips_landscape_and_private_assets(self):
        from unittest.mock import Mock
        data=BytesIO(); Image.new('RGB',(200,300),'gray').save(data,format='JPEG')
        response=Mock(); response.json.return_value=[
            {'id':'landscape','type':'IMAGE','width':300,'height':200,'visibility':'timeline'},
            {'id':'hidden','type':'IMAGE','width':200,'height':300,'visibility':'hidden'},
            {'id':'video','type':'VIDEO','width':200,'height':300,'visibility':'timeline'},
            {'id':'portrait','type':'IMAGE','width':200,'height':300,'visibility':'timeline'}]
        preview=Mock(status_code=200,content=data.getvalue())
        with patch('screens.family_photo.IMMICH_API_KEY','test-key'), patch('screens.family_photo.requests.post',return_value=response), patch('screens.family_photo.requests.get',return_value=preview) as get:
            self.assertEqual(_immich_photo().size,(1200,1600))
            self.assertEqual(get.call_count,1)
            self.assertIn('/portrait/thumbnail',get.call_args.args[0])
            self.assertEqual(get.call_args.kwargs['params'],{'size':'preview'})

    def test_council_dates_cross_year_without_reviving_old_dates(self):
        from screens.bins import _parse_collection_table
        from datetime import date
        markup='<table><tr><td>Monday 4 January</td><td>Recycling &amp; paper</td></tr><tr><td>Friday 25 December</td><td>Old collection</td></tr></table>'
        rows=_parse_collection_table(markup,date(2026,12,30))
        self.assertEqual(rows,[{'binType':'Recycling & paper','collectionDay':'2027-01-04'}])
        with self.assertRaises(shared.ScreenUnavailable):
            _parse_collection_table('<table></table>',date(2026,12,30))

    def test_soap_locations_and_cancellation(self):
        self.assertEqual(_locations({'location':{'crs':'MYB'}}),[{'crs':'MYB'}])
        board={'trainServices':{'service':{'std':'18:10','destination':{'location':{'crs':'MYB','locationName':'London Marylebone'}},'isCancelled':'false','etd':'On time'}}}
        with patch('screens.trains._cache_fetch',return_value=board), patch('screens.trains.TRAINS_DESTINATION','MYB'):
            self.assertEqual(render_trains().size,(WIDTH,HEIGHT))

if __name__=='__main__': unittest.main()
