import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agents.memory_agent import MemoryAgent
from memory.memory_manager import MemoryManager
from memory.redis_client import RedisClient
from core.session import SessionState

@pytest.fixture(autouse=True)
def reset_redis_offline():
    RedisClient._is_offline = False
    yield
    RedisClient._is_offline = False

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.lpush = AsyncMock(return_value=1)
    mock.ltrim = AsyncMock(return_value=True)
    mock.expire = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_db():
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    
    mock_transaction = MagicMock()
    mock_transaction.__aenter__ = AsyncMock()
    mock_transaction.__aexit__ = AsyncMock()
    
    mock_conn.transaction = MagicMock(return_value=mock_transaction)
    
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock()
    
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    return mock_pool

@pytest.mark.asyncio
async def test_memory_manager_session_workflow(mock_redis):
    with patch("memory.redis_client.get_redis", return_value=mock_redis):
        manager = MemoryManager()
        
        # Test save_session
        save_ok = await manager.save_session("user1", {"token": "abc"})
        assert save_ok is True
        mock_redis.set.assert_called_with("session:user1", '{"token": "abc"}', ex=1800)
        
        # Test load_session
        mock_redis.get.return_value = '{"token": "abc"}'
        sess = await manager.load_session("user1")
        assert sess == {"token": "abc"}
        
        # Test invalidate_session
        del_ok = await manager.invalidate_session("user1")
        assert del_ok is True
        mock_redis.delete.assert_any_call("session:user1")
        mock_redis.delete.assert_any_call("story:user1")

@pytest.mark.asyncio
async def test_memory_manager_story_workflow(mock_redis):
    with patch("memory.redis_client.get_redis", return_value=mock_redis):
        manager = MemoryManager()
        
        # Test save_story
        save_ok = await manager.save_story("user1", {"story": "Once upon a time"})
        assert save_ok is True
        mock_redis.set.assert_called_with("story:user1", '{"story": "Once upon a time"}', ex=1800)
        
        # Test load_story
        mock_redis.get.return_value = '{"story": "Once upon a time"}'
        story = await manager.load_story("user1")
        assert story == {"story": "Once upon a time"}

@pytest.mark.asyncio
async def test_memory_manager_save_journey(mock_redis, mock_db):
    with patch("memory.redis_client.get_redis", return_value=mock_redis), \
         patch("memory.memory_manager.get_pool", return_value=mock_db):
        manager = MemoryManager()
        
        save_ok = await manager.save_journey("user1", "Pune", "req123", "Peshwa history")
        assert save_ok is True
        mock_redis.lpush.assert_called_with("places:user1", "Pune")
        
@pytest.mark.asyncio
async def test_memory_agent_execution(mock_redis, mock_db):
    with patch("memory.redis_client.get_redis", return_value=mock_redis), \
         patch("memory.memory_manager.get_pool", return_value=mock_db):
        agent = MemoryAgent()
        state = SessionState({
            "request_id": "req123",
            "request": {"user_id": "user1"},
            "story": {"story": "Awesome historical text"},
            "location": {"place": "Pune"}
        })
        
        result = await agent.execute(state)
        assert result.get("memory_saved") is True

