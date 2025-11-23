import load_env
from strands_tools import get_recent_metrics
from datetime import datetime

class MetricsAnalystAgent:
    def __init__(self):
        self.name = "MetricsAnalyst"
        self.thresholds = {
            'p95_latency_ms': 1500,
            'error_rate': 0.1,
            'cpu_utilization': 80,
            'memory_usage_mb': 200
        }
    
    def analyze_metrics(self, duration_minutes=10):
        thinking_log = [f"Starting metrics analysis for last {duration_minutes} minutes"]
        
        metrics_data = get_recent_metrics(duration_minutes=duration_minutes)
        lambda_metrics = metrics_data.get('lambda_metrics', {})
        custom_metrics = metrics_data.get('custom_metrics', {})
        
        anomalies = []
        
        # Check Lambda duration
        duration_data = lambda_metrics.get('duration', [])
        if duration_data:
            max_duration = max([dp['Maximum'] for dp in duration_data])
            thinking_log.append(f"Max duration observed: {max_duration}ms")
            if max_duration > self.thresholds['p95_latency_ms']:
                anomalies.append({
                    'type': 'latency_spike',
                    'value': max_duration,
                    'severity': 'high'
                })
                thinking_log.append(f"ANOMALY: Latency spike detected - {max_duration}ms")
        
        # Check custom metrics
        cpu_data = custom_metrics.get('CPUUtilization', [])
        if cpu_data:
            max_cpu = max([dp['Maximum'] for dp in cpu_data])
            if max_cpu > self.thresholds['cpu_utilization']:
                anomalies.append({
                    'type': 'cpu_spike',
                    'value': max_cpu,
                    'severity': 'medium'
                })
        
        alert_created = len(anomalies) > 0
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'metrics_anomaly',
            'anomalies': anomalies
        } if alert_created else None
        
        return {
            'alert_created': alert_created,
            'alert': alert,
            'metric_summary': metrics_data,
            'thinking_log': thinking_log
        }