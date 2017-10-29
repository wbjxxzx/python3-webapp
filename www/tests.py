import unittest
import orm, asyncio
from models import User, Blog, Comment

class TestUser(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_init(self):
        u = User()
        self.assertEqual(u, {})

if __name__ == '__main__':
    unittest.main()