"""New offline recovery checks; not the original missing test suite."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from models import AlphaSignal, Subscriber
from publishers.renderers.plaintext import PlaintextRenderer
from publishers.renderers.html import HTMLRenderer
from publishers.email import EmailPublisher
from utils.config import load_sources
from subscribers.tokens import new_token

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.signal = AlphaSignal(id="sample", source_url="https://example.com", source_lang="zh",
            bodies={"zh": "【核心洞察】: <script>alert(1)</script>", "en": "[Core Insight]: Evidence"})
        self.sub = Subscriber(id="offline", address="offline@example.invalid", langs=["zh", "en"])

    def test_plaintext_preserves_oversize_item(self):
        self.assertEqual(PlaintextRenderer(max_bytes=2).render([self.signal], self.sub), [self.signal.bodies['zh']])

    def test_html_escapes_and_includes_languages(self):
        text = HTMLRenderer().render([self.signal], self.sub)[0]
        self.assertNotIn('<script>', text)
        self.assertIn('&lt;script&gt;', text)
        self.assertIn('Evidence', text)

    def test_email_dry_run_never_sends(self):
        pub = EmailPublisher(sender="offline@example.invalid")
        with patch.object(pub, '_send', side_effect=AssertionError('unexpected send')):
            self.assertTrue(pub.publish([self.signal], [self.sub], dry_run=True)[0].success)

    def test_archive_compatible_subscriber(self):
        from publishers import orchestrator
        with tempfile.TemporaryDirectory() as temp, patch.object(orchestrator, 'TEST_OUTPUTS', temp):
            files = orchestrator._archive_locally([self.signal], 'recovery', 1800)
            self.assertEqual(len(files), 1)
            self.assertIn('核心洞察', Path(files[0]).read_text())

    def test_source_registry(self):
        sources = load_sources(str(Path(__file__).resolve().parents[1]))
        self.assertTrue(sources)
        ids = [s['id'] for s in sources]
        self.assertEqual(len(ids), len(set(ids)))

    def test_fetch_due_and_tokens(self):
        from fetch import is_source_due
        self.assertTrue(is_source_due('hourly'))
        self.assertIsInstance(is_source_due('daily'), bool)
        self.assertNotEqual(new_token(), new_token())

if __name__ == '__main__':
    unittest.main()
