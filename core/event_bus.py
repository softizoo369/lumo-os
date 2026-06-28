import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EventBus:
    """
    Explicit Event Dispatcher for Lumo OS.
    Replaces Django Signals to avoid hidden complexity and race conditions.
    """
    
    @staticmethod
    def publish(event_name: str, payload: Dict[str, Any]):
        """
        Publishes an event to the system. 
        Later, this will push messages to Redis/Celery for background processing.
        """
        # MVP: Just logging the event
        logger.info(f"[EVENT PUBLISHED] {event_name.upper()} | Payload: {payload}")
        
        # Example of future implementation:
        # from core.tasks import route_event
        # route_event.delay(event_name, payload)

# Instantiate a global event bus
event_bus = EventBus()