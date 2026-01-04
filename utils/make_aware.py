from datetime import UTC

def make_aware(dt):
    """Transform naive datetime into UTC-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt