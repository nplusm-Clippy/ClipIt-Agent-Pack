import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from scripts import generate_broll, generate_thumbnail


class RecordingClient:
    instances = []

    def __init__(self):
        self.calls = []
        self.__class__.instances.append(self)

    def post(self, path, body):
        self.calls.append((path, body))
        return {"jobId": "job-1"}

    def wait_for_job(self, job_id, timeout):
        self.calls.append(("wait", {"jobId": job_id, "timeout": timeout}))
        return {"status": "completed"}


class MediaGenerationContractTests(unittest.TestCase):
    def setUp(self):
        RecordingClient.instances.clear()

    def test_broll_posts_current_public_request_shape_without_provider_audio(self):
        argv = [
            "generate_broll.py",
            "--clip-id", "clip-1",
            "--start", "2",
            "--end", "8",
            "--prompt", "controlled product reveal",
            "--duration", "6",
            "--resolution", "768p",
            "--image-quality", "high",
        ]
        with patch.object(generate_broll, "ClipperClient", RecordingClient), \
             patch.object(generate_broll, "print_json"), \
             patch("sys.argv", argv):
            generate_broll.main()

        path, body = RecordingClient.instances[-1].calls[0]
        self.assertEqual(path, "/api/v1/clips/clip-1/broll/generate")
        self.assertEqual(body, {
            "clipId": "clip-1",
            "startTimeInClip": 2.0,
            "endTimeInClip": 8.0,
            "mode": "single_image",
            "durationSeconds": 6,
            "resolution": "768p",
            "imageQuality": "high",
            "promptOverride": "controlled product reveal",
        })
        self.assertNotIn("withAudio", body)

    def test_broll_enforces_duration_placement_and_end_frame_contracts(self):
        invalid_argv = [
            "generate_broll.py",
            "--clip-id", "clip-1",
            "--start", "0",
            "--end", "8",
            "--duration", "6",
        ]
        with redirect_stderr(io.StringIO()):
            with patch("sys.argv", invalid_argv), self.assertRaises(SystemExit):
                generate_broll.main()

        missing_end_frame = [
            "generate_broll.py",
            "--clip-id", "clip-1",
            "--start", "0",
            "--end", "5",
            "--duration", "5",
            "--mode", "start_end_frame",
        ]
        with redirect_stderr(io.StringIO()):
            with patch("sys.argv", missing_end_frame), self.assertRaises(SystemExit):
                generate_broll.main()

    def test_thumbnail_posts_quality_reference_choice_and_all_current_ratios(self):
        argv = [
            "generate_thumbnail.py",
            "--clip-id", "clip-1",
            "--prompt", "Change only the background; preserve identity",
            "--aspect-ratio", "3:2",
            "--resolution", "4K",
            "--quality", "high",
            "--no-use-existing-thumbnail",
        ]
        with patch.object(generate_thumbnail, "ClipperClient", RecordingClient), \
             patch.object(generate_thumbnail, "print_json"), \
             patch("sys.argv", argv):
            generate_thumbnail.main()

        path, body = RecordingClient.instances[-1].calls[0]
        self.assertEqual(path, "/api/v1/thumbnails")
        self.assertEqual(body, {
            "prompt": "Change only the background; preserve identity",
            "aspectRatio": "3:2",
            "resolution": "4K",
            "quality": "high",
            "useExistingThumbnail": False,
            "clipId": "clip-1",
        })

    def test_thumbnail_defaults_to_existing_reference_and_omits_optional_quality(self):
        argv = ["generate_thumbnail.py", "--prompt", "Clean editorial still", "--aspect-ratio", "2:3"]
        with patch.object(generate_thumbnail, "ClipperClient", RecordingClient), \
             patch.object(generate_thumbnail, "print_json"), \
             patch("sys.argv", argv):
            generate_thumbnail.main()

        _, body = RecordingClient.instances[-1].calls[0]
        self.assertTrue(body["useExistingThumbnail"])
        self.assertEqual(body["aspectRatio"], "2:3")
        self.assertNotIn("quality", body)
        self.assertNotIn("clipId", body)


if __name__ == "__main__":
    unittest.main()
