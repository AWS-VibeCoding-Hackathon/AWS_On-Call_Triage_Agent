#!/usr/bin/env python3

import load_env  # Load AWS credentials
from orchestrator import IncidentOrchestrator
import json

def main():
    print("AWS Incident Assistant - Starting System")
    print("=" * 50)
    
    orchestrator = IncidentOrchestrator()
    
    try:
        # Run the polling loop
        orchestrator.run_polling_loop(poll_interval=30)
    except KeyboardInterrupt:
        print("\nSystem stopped by user")
        
        # Show any incidents that were created
        incidents = orchestrator.get_incidents()
        if incidents:
            print(f"\nFound {len(incidents)} incidents:")
            for incident in incidents:
                print(f"- {incident['incident_id']}: {incident['root_cause']}")

if __name__ == "__main__":
    main()