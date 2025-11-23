from datetime import datetime

class RootCauseAgent:
    def __init__(self):
        self.name = "RootCauseAgent"
    
    def analyze_root_cause(self, log_summary, metric_summary, alert=None):
        thinking_log = ["Starting root cause analysis"]
        
        key_errors = log_summary.get('key_errors', [])
        anomalies = alert.get('anomalies', []) if alert else []
        
        # Determine root cause
        root_cause = 'healthy_system'
        if anomalies:
            if any(a.get('type') == 'latency_spike' for a in anomalies):
                root_cause = 'performance_degradation'
            elif any(a.get('type') == 'cpu_spike' for a in anomalies):
                root_cause = 'resource_exhaustion'
        
        # Generate recommendations
        recommendations = []
        if root_cause == 'performance_degradation':
            recommendations = [
                'Check downstream service response times',
                'Review Lambda timeout configuration',
                'Monitor for retry patterns'
            ]
        elif root_cause == 'resource_exhaustion':
            recommendations = [
                'Increase Lambda memory allocation',
                'Optimize application resource usage',
                'Review concurrent execution limits'
            ]
        else:
            recommendations = ['System operating normally']
        
        # Create incident note
        incident_note = f"""INCIDENT ANALYSIS - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

ROOT CAUSE: {root_cause.replace('_', ' ').title()}
SUMMARY: {log_summary.get('summary', 'No issues detected')}

RECOMMENDATIONS:
{chr(10).join(f"• {rec}" for rec in recommendations[:3])}
"""
        
        thinking_log.append(f"Root cause determined: {root_cause}")
        
        return {
            'root_cause': root_cause,
            'recommended_action': recommendations[0] if recommendations else 'Monitor system',
            'incident_note': incident_note,
            'thinking_log': thinking_log
        }