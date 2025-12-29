"""
Redis Streams client for event processing
"""

from typing import Dict, List, Optional, Any
import json
import redis.asyncio as redis
import structlog

from src.core.config import settings

logger = structlog.get_logger()


class RedisStreamClient:
    """Redis Streams client for event-driven architecture"""

    STREAM_PUSH_EVENTS = "github:push"
    STREAM_PR_EVENTS = "github:pull_request"
    STREAM_RELEASE_EVENTS = "github:release"
    STREAM_SECURITY_ADVISORIES = "github:security_advisory"

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.redis_client = await redis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        logger.info("Connected to Redis")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def publish_event(
        self,
        stream_name: str,
        event_data: Dict[str, Any],
        max_len: Optional[int] = None,
    ) -> str:
        """
        Publish an event to a Redis stream

        Args:
            stream_name: Name of the stream
            event_data: Event data dictionary
            max_len: Maximum stream length (for trimming)

        Returns:
            Event ID
        """
        if not self.redis_client:
            await self.connect()

        # Serialize complex objects to JSON strings
        serialized_data = {}
        for key, value in event_data.items():
            if isinstance(value, (dict, list)):
                serialized_data[key] = json.dumps(value)
            else:
                serialized_data[key] = str(value)

        event_id = await self.redis_client.xadd(
            stream_name,
            serialized_data,
            maxlen=max_len or settings.STREAM_MAX_LEN,
            approximate=True,
        )

        logger.info("Published event to stream", stream=stream_name, event_id=event_id)

        return event_id

    async def create_consumer_group(self, stream_name: str, group_name: str):
        """
        Create a consumer group for a stream

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
        """
        if not self.redis_client:
            await self.connect()

        try:
            await self.redis_client.xgroup_create(
                stream_name, group_name, id="0", mkstream=True
            )
            logger.info("Created consumer group", stream=stream_name, group=group_name)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            logger.debug(
                "Consumer group already exists", stream=stream_name, group=group_name
            )

    async def consume_events(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block: int = 5000,
    ) -> List[tuple]:
        """
        Consume events from a stream using consumer group

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
            consumer_name: Name of this consumer
            count: Number of events to read
            block: Block time in milliseconds

        Returns:
            List of (event_id, event_data) tuples
        """
        if not self.redis_client:
            await self.connect()

        # Ensure consumer group exists
        await self.create_consumer_group(stream_name, group_name)

        # Read from stream
        events = await self.redis_client.xreadgroup(
            group_name, consumer_name, {stream_name: ">"}, count=count, block=block
        )

        if not events:
            return []

        # Parse events
        parsed_events = []
        for stream, messages in events:
            for event_id, event_data in messages:
                # Deserialize JSON fields
                deserialized_data = {}
                for key, value in event_data.items():
                    try:
                        deserialized_data[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        deserialized_data[key] = value

                parsed_events.append((event_id, deserialized_data))

        return parsed_events

    async def acknowledge_event(self, stream_name: str, group_name: str, event_id: str):
        """
        Acknowledge an event as processed

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
            event_id: ID of the event to acknowledge
        """
        if not self.redis_client:
            await self.connect()

        await self.redis_client.xack(stream_name, group_name, event_id)

        logger.debug("Acknowledged event", stream=stream_name, event_id=event_id)

    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """Get information about a stream"""
        if not self.redis_client:
            await self.connect()

        return await self.redis_client.xinfo_stream(stream_name)


# Global Redis client instance
redis_stream_client = RedisStreamClient()
