import unittest

from services.worker_layer import WorkerLayer


class WorkerLayerTests(unittest.TestCase):
    def test_dispatch_cache_cleanup_inline(self):
        layer = WorkerLayer(use_celery=False)

        handle = layer.dispatch_cache_cleanup()

        self.assertEqual(handle.status, "completed")
        self.assertIn("renders", handle.result)
        self.assertIn("pdf_temp", handle.result)


if __name__ == "__main__":
    unittest.main()
