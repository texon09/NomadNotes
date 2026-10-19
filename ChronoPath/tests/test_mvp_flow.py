import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from agents.supervisor import SupervisorAgent


class MvpFlowTest(unittest.TestCase):
    @patch("agents.location_agent.genai.Client")
    @patch("agents.location_agent.reverse_geocode")
    @patch("agents.location_agent.heritage_lookup")
    @patch("agents.location_agent.fetch_history")
    def test_success_condition_for_shaniwar_wada(self, mock_history, mock_heritage, mock_geo, mock_client_cls):
        import asyncio
        async def mock_geo_resp(*args):
            return {"city": "Pune", "state": "MH", "country": "IN", "lat": 18.5196, "lng": 73.8553, "display_name": "Pune"}
        async def mock_heritage_resp(*args):
            return {"place": "Shaniwar Wada", "lat": 18.5196, "lng": 73.8553, "distance_km": 0.1, "period": "Peshwa Era", "themes": ["History"], "summary": "Seat of Peshwas"}
        async def mock_history_resp(*args):
            return {"context": "Peshwa Era", "facts": ["Built in 1732"]}
            
        mock_geo.side_effect = mock_geo_resp
        mock_heritage.side_effect = mock_heritage_resp
        mock_history.side_effect = mock_history_resp

        # Mock the Router LLM to force fallback to fetch_history
        mock_client = MagicMock()
        mock_aio_response = MagicMock()
        mock_aio_response.text = '{"is_famous": false}'
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_aio_response)

        def mock_generate_content(*args, **kwargs):
            contents = kwargs.get("contents", "")
            if isinstance(contents, str) and "Historical Editor" in contents:
                return MagicMock(text='{"pass": true, "score": 10, "feedback": ""}')
            if isinstance(contents, str) and "travel assistant" in contents:
                return MagicMock(text='[]')
            return MagicMock(text="Welcome to Shaniwar Wada. This historic seat of the Peshwas...")

        mock_client.models.generate_content.side_effect = mock_generate_content
        mock_client_cls.return_value = mock_client

        response = SupervisorAgent().run(
            {
                "user": "1",
                "lat": 18.5196,
                "lng": 73.8553,
            }
        )

        self.assertEqual(response["place"]["name"], "Shaniwar Wada")
        self.assertIn("Peshwa Era", response["text"]["title"])
        self.assertTrue(response["text"]["story"])
        self.assertTrue(response["safe"])


if __name__ == "__main__":
    unittest.main()
