import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestExampleAPI(unittest.TestCase):
    """测试示例API"""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_get_example(self):
        """测试GET /api/v1/example端点"""
        response = self.client.get("/api/v1/example")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())
    
    def test_post_example(self):
        """测试POST /api/v1/example端点"""
        test_data = {"name": "Test", "value": "123"}
        response = self.client.post("/api/v1/example", json=test_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())
        self.assertIn("data", response.json())
        self.assertEqual(response.json()["data"], test_data)


if __name__ == "__main__":
    unittest.main()
