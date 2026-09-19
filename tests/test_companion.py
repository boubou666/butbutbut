import unittest

from butbutbut import companion


class TestBind(unittest.TestCase):
    def test_the_default_is_local_only(self):
        self.assertEqual(companion.parse_bind(""), ("127.0.0.1", 8765))

    def test_a_port_stays_local(self):
        self.assertEqual(companion.parse_bind("9000"), ("127.0.0.1", 9000))

    def test_lan_access_must_be_explicit(self):
        self.assertEqual(companion.parse_bind("0.0.0.0:9000"),
                         ("0.0.0.0", 9000))

    def test_an_invalid_port_is_refused(self):
        with self.assertRaises(companion.Invalid):
            companion.parse_bind("70000")


class TestPage(unittest.TestCase):
    def test_the_page_has_no_remote_resource(self):
        self.assertNotIn("https://", companion.PAGE)
        self.assertNotIn("http://", companion.PAGE)
        self.assertIn("/api/state", companion.PAGE)
        self.assertIn("/api/sync", companion.PAGE)


if __name__ == "__main__":
    unittest.main()
