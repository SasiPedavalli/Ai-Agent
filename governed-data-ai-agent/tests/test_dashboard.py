import unittest

from fastapi.testclient import TestClient

from dashboard.server import app


class DashboardApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.csv = self.client.get('/api/sample').text

    def test_approved_sample_allows(self):
        response = self.client.post('/api/analyze?asset_name=customer_events&owner=data-platform%40company.com&domain=customer-telemetry&environment=test&approved=true&lineage_registered=true', content=self.csv, headers={'content-type': 'text/csv'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['policy']['decision'], 'ALLOW')
        self.assertIn('input_output_traceability', payload['trace'])

    def test_unapproved_sample_blocks(self):
        response = self.client.post('/api/analyze?asset_name=customer_events&owner=data-platform%40company.com&domain=customer-telemetry&environment=test&approved=false&lineage_registered=true', content=self.csv, headers={'content-type': 'text/csv'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['policy']['decision'], 'BLOCK')
        self.assertIn('approved_governed_source', payload['policy']['reasons'])


if __name__ == '__main__':
    unittest.main()
