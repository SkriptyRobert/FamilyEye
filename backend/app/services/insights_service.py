"""
Smart Insights Service.

Calculates focus metrics, wellness scores, and anomaly detection
for user activity data.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dateutil import parser

logger = logging.getLogger("insights")


class InsightsService:
    """Calculate Smart Insights metrics from usage logs."""
    
    # Configuration constants
    FOCUS_GRACE_PERIOD = 30  # seconds - time between focus events to merge
    MIN_DEEP_WORK_DURATION = 15 * 60  # 15 minutes in seconds
    NIGHT_OWL_HOUR = 22  # 10 PM
    
    def __init__(self):
        """Initialize the insights service."""
        pass
    
    def calculate_focus_metrics(
        self, 
        logs: List[Tuple], 
        total_screen_time: int
    ) -> Dict:
        """
        Calculate focus metrics from usage logs.
        
        Args:
            logs: List of (app_name, timestamp, duration, is_focused) tuples
            total_screen_time: Total screen time in seconds for flow index calculation
            
        Returns:
            Dict with deep_work_seconds, context_switches, flow_index
        """
        if not logs:
            return {
                "deep_work_seconds": 0,
                "context_switches": 0,
                "flow_index": 0
            }
        
        # ONLY collect segments from is_focused=True logs
        focused_segments = []
        
        for log in logs:
            app_name, timestamp, duration, is_focused = log
            
            # STRICT: Only focused apps count toward deep work
            if not is_focused:
                continue
            
            ts_obj = self._parse_timestamp(timestamp)
            start_ts = ts_obj.timestamp()
            end_ts = start_ts + duration
            focused_segments.append((start_ts, end_ts, app_name))
        
        # Merge overlapping segments into continuous work blocks
        merged_intervals = self._merge_intervals(focused_segments)
        
        logger.debug(
            f"Focus analysis: {len(focused_segments)} focused segments -> "
            f"{len(merged_intervals)} merged intervals"
        )
        
        # Calculate Deep Work (only blocks >= 15 minutes)
        deep_work_seconds = sum(
            (end - start) 
            for start, end in merged_intervals 
            if (end - start) >= self.MIN_DEEP_WORK_DURATION
        )
        
        # Context switches: gaps between focused work blocks
        context_switches = max(0, len(merged_intervals) - 1)
        
        # Flow Index = (Deep Work / Screen Time) * 100, capped at 100
        flow_index = 0
        if total_screen_time > 0:
            flow_index = min(100, round((deep_work_seconds / total_screen_time * 100), 1))
        
        logger.debug(f"Deep work: {deep_work_seconds}s, Context switches: {context_switches}")
        
        return {
            "deep_work_seconds": int(deep_work_seconds),
            "context_switches": context_switches,
            "flow_index": flow_index
        }
    
    def _merge_intervals(self, segments: List[Tuple]) -> List[Tuple]:
        """
        Merge overlapping time segments with grace period tolerance.
        
        Args:
            segments: List of (start_ts, end_ts, app_name) tuples
            
        Returns:
            List of (start_ts, end_ts) merged intervals
        """
        if not segments:
            return []
        
        segments.sort(key=lambda x: x[0])
        merged = []
        
        current_start, current_end, _ = segments[0]
        
        for i in range(1, len(segments)):
            next_start, next_end, _ = segments[i]
            
            # Merge if overlapping or within grace period
            if next_start <= (current_end + self.FOCUS_GRACE_PERIOD):
                current_end = max(current_end, next_end)
            else:
                merged.append((current_start, current_end))
                current_start, current_end = next_start, next_end
        
        merged.append((current_start, current_end))
        return merged
    
    def _parse_timestamp(self, timestamp) -> datetime:
        """Parse timestamp to datetime object."""
        if hasattr(timestamp, 'timestamp'):
            return timestamp
        return parser.parse(timestamp)
    
    def calculate_anomalies(
        self,
        logs_today: List[Tuple],
        historical_starts: List[float],
        offset_seconds: int = 0
    ) -> Dict:
        """
        Detect anomalies in usage patterns.
        
        Args:
            logs_today: Today's usage logs
            historical_starts: List of start hours from previous days
            offset_seconds: Device timezone offset
            
        Returns:
            Dict with is_early_start, is_night_owl, avg_start_hour
        """
        is_early_start = False
        is_night_owl = False
        avg_start_hour = None
        
        if not logs_today:
            return {
                "is_early_start": is_early_start,
                "is_night_owl": is_night_owl,
                "avg_start_hour": avg_start_hour
            }
        
        first_activity = logs_today[0][1]
        first_dt = self._parse_timestamp(first_activity)
        
        # Night Owl: Any session after 22:00
        for log in logs_today:
            l_dt = self._parse_timestamp(log[1])
            if l_dt.hour >= self.NIGHT_OWL_HOUR:
                is_night_owl = True
                break
        
        # Early Start: Compare to average from historical data
        if historical_starts:
            avg_start_hour = sum(historical_starts) / len(historical_starts)
            current_hour = first_dt.hour + first_dt.minute / 60
            if current_hour < (avg_start_hour - 1.5):
                is_early_start = True
        
        return {
            "is_early_start": is_early_start,
            "is_night_owl": is_night_owl,
            "avg_start_hour": round(avg_start_hour, 1) if avg_start_hour else None
        }
    
    def calculate_wellness_score(
        self,
        total_minutes: float,
        is_night_owl: bool,
        forced_terminations: int
    ) -> Dict:
        """
        Calculate wellness score based on usage patterns.
        
        Args:
            total_minutes: Total screen time in minutes
            is_night_owl: Whether user was active after 10 PM
            forced_terminations: Number of apps that hit their limit
            
        Returns:
            Dict with wellness_score and usage_intensity
        """
        # Base score calculation
        if total_minutes <= 120:
            # 0-120 mins: Slow linear decay (100 -> 80)
            base_score = 100 - (total_minutes / 120 * 20)
        else:
            # > 120 mins: Rapid decay (-20 per extra hour)
            extra_hours = (total_minutes - 120) / 60
            base_score = 80 - (extra_hours * 20)
        
        # Penalties
        if is_night_owl:
            base_score -= 15
        base_score -= (forced_terminations * 10)
        
        # Clamp to [0, 100]
        wellness_score = max(0, min(100, round(base_score)))
        
        # Usage intensity classification
        if total_minutes > 240:
            intensity = "High"
        elif total_minutes > 120:
            intensity = "Moderate"
        else:
            intensity = "Low"
        
        return {
            "wellness_score": wellness_score,
            "usage_intensity": intensity
        }


# Global singleton instance
insights_service = InsightsService()
