import time
import json
from datetime import datetime
from agents.metrics_analyst import MetricsAnalystAgent
from agents.log_investigator import LogInvestigatorAgent
from agents.root_cause_agent import RootCauseAgent

class IncidentOrchestrator:
    def __init__(self):
        self.metrics_agent = MetricsAnalystAgent()
        self.log_agent = LogInvestigatorAgent()
        self.root_cause_agent = RootCauseAgent()
        self.incidents = []
    
    def run_polling_loop(self, poll_interval=60):
        """Main polling loop - checks for anomalies every poll_interval seconds"""
        print(f"Starting incident detection polling (every {poll_interval}s)")
        
        while True:
            try:
                # Run metrics analysis
                metrics_result = self.metrics_agent.analyze_metrics(duration_minutes=10)
                
                if metrics_result['alert_created']:
                    print(f"Alert detected! Creating incident...")
                    incident = self.create_incident(metrics_result['alert'])
                    print(f"Incident {incident['incident_id']} created and analyzed")
                
                time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                print("Stopping orchestrator...")
                break
            except Exception as e:
                print(f"Error in polling loop: {e}")
                time.sleep(poll_interval)
    
    def create_incident(self, alert):
        """Create and fully analyze an incident"""
        incident_id = f"INC-{int(time.time())}"
        
        # Step 1: Log investigation
        log_result = self.log_agent.investigate_logs(duration_minutes=15)
        
        # Step 2: Focused metrics analysis
        focused_metrics = self.metrics_agent.analyze_metrics(duration_minutes=15)
        
        # Step 3: Root cause analysis
        root_cause_result = self.root_cause_agent.analyze_root_cause(
            log_result, 
            focused_metrics['metric_summary'], 
            alert
        )
        
        # Step 4: Assemble incident
        incident = {
            'incident_id': incident_id,
            'created_at': datetime.utcnow().isoformat(),
            'alert': alert,
            'log_summary': log_result,
            'metric_summary': focused_metrics['metric_summary'],
            'root_cause': root_cause_result['root_cause'],
            'recommended_action': root_cause_result['recommended_action'],
            'incident_note': root_cause_result['incident_note'],
            'thinking_log': self._merge_thinking_logs([
                log_result['thinking_log'],
                focused_metrics['thinking_log'],
                root_cause_result['thinking_log']
            ])
        }
        
        self.incidents.append(incident)
        return incident
    
    def _merge_thinking_logs(self, log_lists):
        """Merge thinking logs from all agents"""
        merged = []
        for i, logs in enumerate(log_lists):
            agent_names = ['LogInvestigator', 'MetricsAnalyst', 'RootCauseAgent']
            for log in logs:
                merged.append(f"[{agent_names[i]}] {log}")
        return merged
    
    def get_incidents(self):
        """Return all incidents"""
        return self.incidents