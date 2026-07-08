# backend/app/core/log_buffer.py
from collections import deque

log_ring_buffer = deque(maxlen=100)

def ring_buffer_processor(logger, method_name, event_dict):
    log_ring_buffer.append(dict(event_dict))
    return event_dict