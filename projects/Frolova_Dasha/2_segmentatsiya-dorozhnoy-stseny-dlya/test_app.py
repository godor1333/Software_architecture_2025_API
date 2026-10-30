import tempfile
import unittest
from pathlib import Path
from PIL import Image
from unittest.mock import patch
import app
import api

class SceneTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); app.DB_PATH=Path(self.tmp.name)/"scene.db"; app.ARTIFACTS=Path(self.tmp.name)/"artifacts"; app.ARTIFACTS.mkdir()
    def tearDown(self): self.tmp.cleanup()
    def test_red_region_is_car(self):
        im=Image.new("RGB",(10,10),(220,30,30)); mask, totals=app.segment(im); self.assertEqual(totals["car"],100); self.assertEqual(mask.getpixel((5,5)),app.PALETTE["car"])
    def test_configured_strategy_returns_model_mask(self):
        expected=Image.new('RGB',(2,2),app.PALETTE['car'])
        with patch.object(app,'SegFormerAdapter') as adapter:
            adapter.return_value.predict.return_value=expected
            mask,totals=app.segmentation_strategy('configured').predict(Image.new('RGB',(2,2)))
        self.assertEqual(totals['car'],4);self.assertEqual(mask.getpixel((0,0)),app.PALETTE['car'])
        self.assertIsInstance(app.segmentation_strategy(None),app.ColorSegmentationStrategy)
    def test_store_and_read_frame(self):
        im=Image.new("RGB",(5,5),(80,80,80)); p=app.ARTIFACTS/"x.png"; im.save(p); app.store_frame("f1","fl1",p.read_bytes()); self.assertEqual(app.get_frame("f1")["frame_id"],"f1")

    def test_pedestrian_class_in_generated_frame(self):
        image = Image.new('RGB', (10, 10), app.PALETTE['road'])
        for x in range(2, 4):
            for y in range(3, 8):
                image.putpixel((x, y), app.PALETTE['pedestrian'])
        frame = app.ARTIFACTS / 'pedestrian_input.png'
        image.save(frame)
        with patch.dict('os.environ', {'SEGMENTATION_MODEL': '', 'PRODUCTION_MODE': ''}):
            result = app.store_frame('pedestrian-test', 'test-flight', frame.read_bytes())
        self.assertEqual(result['class_share']['pedestrian'], 0.1)
        mask = Image.open(app.ARTIFACTS / result['mask'])
        self.assertEqual(mask.getpixel((2, 3)), app.PALETTE['pedestrian'])

    def test_preprocessing_normalizes_orientation_and_size(self):
        image = Image.new('RGBA', (2000, 1000), (80, 80, 80, 255))
        prepared = app.FramePreprocessor().process(image)
        self.assertEqual(prepared.mode, 'RGB')
        self.assertLessEqual(prepared.width, 1280)
        self.assertLessEqual(prepared.height, 720)

    def test_scene_analytics_and_dashboard_endpoints(self):
        image = Image.new('RGB', (10, 10), app.PALETTE['road'])
        image.save(app.ARTIFACTS / 'analytics.png')
        app.store_frame('analytics-1', 'flight-a', (app.ARTIFACTS / 'analytics.png').read_bytes())
        data = app.analytics('flight-a')
        self.assertEqual(data['frames'], 1)
        self.assertEqual(data['items'][0]['dominant_class'], 'road')
        self.assertEqual(api.analytics('flight-a')['frames'], 1)
        dashboard = api.dashboard('flight-a')
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn('Scene Analytics Dashboard', dashboard.body.decode('utf-8'))

    def test_video_stream_adapter_processes_ordered_frames(self):
        from video_pipeline import create_demo_video, process_video
        video = create_demo_video(app.ARTIFACTS / 'test_stream.mp4', frame_count=3)
        result = process_video(video, 'flight-video', max_frames=3)
        self.assertEqual(result['frames_processed'], 3)
        self.assertEqual(app.analytics('flight-video')['frames'], 3)

    def test_frame_id_is_safe_for_artifact_paths(self):
        with self.assertRaises(ValueError):
            app.store_frame('../escape', 'flight-a', b'bad')

    def test_uavid_evaluator_preserves_distinct_car_and_person_labels(self):
        from evaluate_uavid import UAVID
        self.assertIn((192, 0, 192), UAVID['car'])
        self.assertIn((64, 0, 128), UAVID['car'])
        self.assertEqual(UAVID['pedestrian'], [(64, 64, 0)])

if __name__ == "__main__": unittest.main()
