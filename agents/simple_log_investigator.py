import load_env
from strands_tools import get_recent_logs
import json

class LogInvestigatorAgent:
    def __init__(self):
        self.name = "LogInvestigator"
    
    def investigate_logs(self, log_group="/aws/lambda/cloudwatch-log-generator", duration_minutes=10):
        thinking_log = [f"Starting log investigation for {log_group}"]
        
        log_events = get_recent_logs(log_group, duration_minutes)
        thinking_log.append(f"Retrieved {len(log_events)} log events")
        
        key_errors = []
        latency_patterns = []
        
        for event in log_events:
            message = event.get('message', '')
            timestamp = event.get('timestamp', 0)
            
            # Parse JSON logs
            try:
                if message.startswith('{'):
                    log_data = json.loads(message)
                    level = log_data.get('level', 'INFO')
                    
                    if level == 'ERROR':
                        key_errors.append({
                            'timestamp': timestamp,
                            'message': log_data.get('message', ''),
                            'scenario': log_data.get('scenario', 'unknown')
                        })
                    
                    # Check for latency patterns
                    if 'latency' in message.lower():
                        latency_patterns.append({
                            'timestamp': timestamp,
                            'message': log_data.get('message', ''),
                            'scenario': log_data.get('scenario', 'unknown')
                        })
                        
            except json.JSONDecodeError:
                if 'ERROR' in message or 'timeout' in message.lower():
                    key_errors.append({
                        'timestamp': timestamp,
                        'message': message
                    })
        
        summary = f"Analyzed {len(log_events)} events, found {len(key_errors)} errors"
        thinking_log.append(f"Investigation complete: {summary}")
        
        return {
            'summary': summary,
            'key_errors': key_errors,
            'latency_patterns': latency_patterns,
            'thinking_log': thinking_log
        }