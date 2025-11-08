"""
Time range parsing utility for infrastructure troubleshooting.
Converts natural language time expressions to timestamps.
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
import re
from zoneinfo import ZoneInfo


class TimeRangeParser:
    """Parse natural language time ranges into timestamps."""
    
    def __init__(self, timezone: str = "UTC"):
        self.timezone = ZoneInfo(timezone)
    
    def parse(self, time_expression: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Parse time expression and return (start_time, end_time).
        
        Examples:
            "last 30 minutes" -> (now - 30min, now)
            "2pm to 3pm" -> (today 14:00, today 15:00)
            "from 14:00 to 15:30" -> (today 14:00, today 15:30)
            "since 2pm" -> (today 14:00, now)
            "yesterday" -> (yesterday 00:00, yesterday 23:59)
        
        Returns:
            Tuple of (start_time, end_time) as datetime objects, or (None, None) if parsing fails
        """
        text = time_expression.lower().strip()
        now = datetime.now(self.timezone)
        
        # Pattern: "last X minutes/hours/days"
        if match := re.search(r'last (\d+) (minute|hour|day)s?', text):
            value = int(match.group(1))
            unit = match.group(2)
            
            if unit == 'minute':
                start_time = now - timedelta(minutes=value)
            elif unit == 'hour':
                start_time = now - timedelta(hours=value)
            else:  # day
                start_time = now - timedelta(days=value)
            
            return (start_time, now)
        
        # Pattern: "X to Y" or "from X to Y"
        if match := re.search(r'(?:from )?(\d{1,2}):?(\d{2})?\s*(?:am|pm)?\s*to\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?', text):
            start_hour = int(match.group(1))
            start_min = int(match.group(2)) if match.group(2) else 0
            end_hour = int(match.group(3))
            end_min = int(match.group(4)) if match.group(4) else 0
            
            # Handle AM/PM
            if 'pm' in text and start_hour < 12:
                start_hour += 12
            if match.group(5) == 'pm' and end_hour < 12:
                end_hour += 12
            
            start_time = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            end_time = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
            
            # If end time is before start time, assume it's next day
            if end_time < start_time:
                end_time += timedelta(days=1)
            
            return (start_time, end_time)
        
        # Pattern: "since X"
        if match := re.search(r'since (\d{1,2}):?(\d{2})?\s*(am|pm)?', text):
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            
            if match.group(3) == 'pm' and hour < 12:
                hour += 12
            
            start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If start time is in the future, assume it was yesterday
            if start_time > now:
                start_time -= timedelta(days=1)
            
            return (start_time, now)
        
        # Pattern: "yesterday"
        if 'yesterday' in text:
            yesterday = now - timedelta(days=1)
            start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return (start_time, end_time)
        
        # Pattern: "today"
        if 'today' in text:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return (start_time, now)
        
        # Pattern: "past hour"
        if 'past hour' in text or 'last hour' in text:
            start_time = now - timedelta(hours=1)
            return (start_time, now)
        
        return (None, None)
    
    def format_timestamp(self, dt: datetime) -> str:
        """Format datetime as Unix timestamp (seconds)."""
        return str(int(dt.timestamp()))
    
    def format_iso(self, dt: datetime) -> str:
        """Format datetime as ISO 8601 string."""
        return dt.isoformat()
    
    def format_human(self, dt: datetime) -> str:
        """Format datetime as human-readable string."""
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    def get_range_summary(self, start_time: datetime, end_time: datetime) -> str:
        """Generate a human-readable summary of the time range."""
        duration = end_time - start_time
        
        if duration.total_seconds() < 3600:
            minutes = int(duration.total_seconds() / 60)
            duration_str = f"{minutes} minutes"
        elif duration.total_seconds() < 86400:
            hours = int(duration.total_seconds() / 3600)
            duration_str = f"{hours} hours"
        else:
            days = int(duration.total_seconds() / 86400)
            duration_str = f"{days} days"
        
        return f"{self.format_human(start_time)} to {self.format_human(end_time)} ({duration_str})"


# Example usage
if __name__ == "__main__":
    parser = TimeRangeParser()
    
    test_cases = [
        "last 30 minutes",
        "2pm to 3pm",
        "from 14:00 to 15:30",
        "since 2pm",
        "yesterday",
        "last 2 hours",
    ]
    
    for test in test_cases:
        start, end = parser.parse(test)
        if start and end:
            print(f"\n'{test}':")
            print(f"  Start: {parser.format_human(start)}")
            print(f"  End:   {parser.format_human(end)}")
            print(f"  Summary: {parser.get_range_summary(start, end)}")
