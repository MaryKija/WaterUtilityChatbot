"""
System Metrics and Health Monitoring

Provides real-time metrics for system health, performance, and AI accuracy.
"""

from typing import Dict, Any
from datetime import datetime
from collections import defaultdict
import time


class MetricsCollector:
    """Collect and track system metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = datetime.now()
        
        # Request metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.request_times = []
        
        # Intent metrics
        self.intent_counts = defaultdict(int)
        self.intent_accuracy = defaultdict(lambda: {'correct': 0, 'total': 0})
        
        # Fallback metrics
        self.fallback_count = 0
        self.clarification_count = 0
        self.menu_selection_count = 0
        
        # Tool metrics
        self.tool_usage = defaultdict(int)
        self.tool_errors = defaultdict(int)
        
        # Session metrics
        self.active_sessions = 0
        self.total_sessions = 0
        self.avg_session_length = 0
    
    def record_request(self, duration: float, success: bool = True):
        """Record a request."""
        self.total_requests += 1
        self.request_times.append(duration)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def record_intent(self, intent: str):
        """Record intent classification."""
        self.intent_counts[intent] += 1
    
    def record_intent_accuracy(self, intent: str, correct: bool):
        """Record intent accuracy."""
        self.intent_accuracy[intent]['total'] += 1
        if correct:
            self.intent_accuracy[intent]['correct'] += 1
    
    def record_fallback(self):
        """Record a fallback event."""
        self.fallback_count += 1
    
    def record_clarification(self):
        """Record a clarification event."""
        self.clarification_count += 1
    
    def record_menu_selection(self):
        """Record a menu selection."""
        self.menu_selection_count += 1
    
    def record_tool_usage(self, tool_name: str, success: bool = True):
        """Record tool usage."""
        self.tool_usage[tool_name] += 1
        if not success:
            self.tool_errors[tool_name] += 1
    
    def record_session(self, active: int, total: int, avg_length: float):
        """Record session metrics."""
        self.active_sessions = active
        self.total_sessions = total
        self.avg_session_length = avg_length
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate averages
        avg_request_time = (
            sum(self.request_times) / len(self.request_times)
            if self.request_times else 0
        )
        
        success_rate = (
            self.successful_requests / self.total_requests * 100
            if self.total_requests > 0 else 0
        )
        
        # Calculate intent accuracy
        intent_accuracy_map = {}
        for intent, stats in self.intent_accuracy.items():
            if stats['total'] > 0:
                accuracy = stats['correct'] / stats['total'] * 100
                intent_accuracy_map[intent] = {
                    'accuracy': accuracy,
                    'correct': stats['correct'],
                    'total': stats['total']
                }
        
        # Overall accuracy
        total_correct = sum(s['correct'] for s in self.intent_accuracy.values())
        total_tests = sum(s['total'] for s in self.intent_accuracy.values())
        overall_accuracy = (
            total_correct / total_tests * 100
            if total_tests > 0 else 0
        )
        
        # Tool error rates
        tool_error_rates = {}
        for tool, count in self.tool_usage.items():
            errors = self.tool_errors.get(tool, 0)
            error_rate = errors / count * 100 if count > 0 else 0
            tool_error_rates[tool] = {
                'usage_count': count,
                'error_count': errors,
                'error_rate': error_rate
            }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime,
            'requests': {
                'total': self.total_requests,
                'successful': self.successful_requests,
                'failed': self.failed_requests,
                'success_rate': success_rate,
                'avg_time_ms': avg_request_time * 1000
            },
            'intents': {
                'total_classifications': sum(self.intent_counts.values()),
                'unique_intents': len(self.intent_counts),
                'top_intents': dict(sorted(
                    self.intent_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]),
                'accuracy': {
                    'overall': overall_accuracy,
                    'by_intent': intent_accuracy_map
                }
            },
            'fallbacks': {
                'total_fallbacks': self.fallback_count,
                'clarifications': self.clarification_count,
                'menu_selections': self.menu_selection_count,
                'fallback_rate': (
                    self.fallback_count / self.total_requests * 100
                    if self.total_requests > 0 else 0
                )
            },
            'tools': {
                'total_usage': sum(self.tool_usage.values()),
                'by_tool': tool_error_rates
            },
            'sessions': {
                'active': self.active_sessions,
                'total': self.total_sessions,
                'avg_length': self.avg_session_length
            },
            'health': {
                'status': self._get_health_status(success_rate, overall_accuracy),
                'issues': self._get_health_issues(success_rate, overall_accuracy)
            }
        }
    
    def _get_health_status(self, success_rate: float, accuracy: float) -> str:
        """Determine system health status."""
        if success_rate >= 95 and accuracy >= 80:
            return "healthy"
        elif success_rate >= 85 and accuracy >= 70:
            return "degraded"
        else:
            return "unhealthy"
    
    def _get_health_issues(self, success_rate: float, accuracy: float) -> list:
        """Identify health issues."""
        issues = []
        
        if success_rate < 95:
            issues.append(f"Low success rate: {success_rate:.1f}%")
        
        if accuracy < 80:
            issues.append(f"Low intent accuracy: {accuracy:.1f}%")
        
        if self.fallback_count > self.total_requests * 0.2:
            issues.append(f"High fallback rate: {self.fallback_count / self.total_requests * 100:.1f}%")
        
        return issues


# Global metrics collector
metrics_collector = MetricsCollector()
