#  AWS On-Call Triage Agent

An AI-powered incident detection and root cause analysis system for AWS CloudWatch. Built with a multi-agent architecture using local LLMs (Llama 3.1) to automatically detect, analyze, and diagnose production incidents.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![AWS](https://img.shields.io/badge/AWS-CloudWatch-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

##  Demo Video

[![Watch Demo](https://img.shields.io/badge/▶️_Watch-Demo_Video-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/watch?v=8-itfsCbIWY)

See the system in action! Watch our [demo video on YouTube](https://www.youtube.com/watch?v=8-itfsCbIWY) to see how the AI agents detect incidents, perform root cause analysis, and provide actionable recommendations in real-time.

##  Overview

On-Call Triage Agent continuously monitors AWS CloudWatch logs and metrics, using specialized AI agents to:
-  **Detect incidents** through metric threshold analysis
-  **Analyze log patterns** to identify error signatures
-  **Perform root cause analysis** with actionable recommendations
-  **Visualize incidents** through an interactive dashboard
-  **Maintain audit trails** with structured incident logging

### Key Features

- **Multi-Agent Architecture**: Specialized agents for metrics analysis, log analysis, and RCA
- **Token Optimization**: 97% reduction in token usage (45K → 3.5K) while preserving insights
- **Local LLM**: Uses Ollama with Llama 3.1 (no data leaves your network)
- **Real-time Monitoring**: Analyzes CloudWatch data on-demand or continuously
- **Structured Logging**: Complete audit trail in JSONL format with unique incident IDs
- **Interactive Dashboard**: Streamlit-based UI with auto-refresh and trend visualization
- **AWS Native**: Integrates seamlessly with CloudWatch Logs and Metrics

##  Architecture

```
┌─────────────────────┐
│  Lambda Simulator   │ ← Generates test incidents
│  (Order Processing) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  AWS CloudWatch     │
│  • Logs             │
│  • Metrics          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Orchestrator      │ ← Fetches data every N minutes
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Data Preprocessor  │ ← Reduces tokens by 97%
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Agent 1: Metrics   │ ← Analyzes metrics, assigns severity
│  Analysis Agent     │
└──────────┬──────────┘
           │
           ▼ (if severity ≥ warning)
┌─────────────────────┐
│  Agent 2: Log       │ ← Detects error patterns, issues
│  Analysis Agent     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Agent 3: RCA       │ ← Root cause + recommendations
│  Agent              │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Incident Logger    │ ← Persists to disk with UUID
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Dashboard          │ ← Streamlit UI for visualization
│  (Streamlit)        │
└─────────────────────┘
```

##  Installation

### Prerequisites

- Python 3.8+
- AWS Account with CloudWatch access
- Ollama with Llama 3.1:8b model
- AWS credentials configured

### 1. Clone the Repository

```bash
cd AWS_Cloud-Ops_Agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Core dependencies:
- `boto3` - AWS SDK for CloudWatch access
- `strands-agents` - Multi-agent framework
- `python-dotenv` - Environment configuration
- `pydantic` - Data validation

### 3. Install Ollama and Llama 3.1

```bash
# Install Ollama (if not already installed)
# Visit: https://ollama.ai

# Pull the Llama 3.1 model
ollama pull llama3.1:8b

# Verify installation
ollama list
```

### 4. Configure Environment Variables

Create a `.env` file:

```bash
# AWS Configuration
AWS_REGION=us-east-1
LOG_GROUP_NAME=/aws/lambda/your-lambda-function
NAMESPACE=CustomApp

# Ollama Configuration
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:8b

# System Configuration (optional)
SEVERITY_THRESHOLD=warning
POLL_INTERVAL_SECONDS=60
```

### 5. Configure AWS Credentials

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Option 3: IAM role (for EC2/Lambda)
```

**Required IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

### 6. Verify Installation

```bash
python check_credentials.py
```

##  Quick Start

### Basic Usage

```bash
# Run incident detection (single execution)
python start_incident_assistant.py
```

**Expected Output:**
```
============================================================
🔍 Starting incident detection cycle...
============================================================
📊 Fetched 18 log events
📈 Fetched metrics for 7 metric types
   - CPUUtilization: 13 datapoints
   - MemoryUsageMB: 13 datapoints
   - OrderLatencyMS: 13 datapoints
 Raw data logged to incident file

 Running Metrics Analysis Agent...
   📏 Raw metrics size: 20,347 chars → Preprocessed for LLM
   Severity: critical

  INCIDENT DETECTED! Running deeper analysis...

 Running Log Analysis Agent...
   📏 Raw logs size: 152,834 chars → Preprocessed for LLM
   Issues detected: 5

 Running RCA Agent...
   Root cause: High CPU utilization (92%+), memory pressure...

 Incident analysis complete!
============================================================
```

### View Results in Dashboard

```bash
# In a separate terminal
streamlit run dashboard.py
```

Dashboard opens at `http://localhost:8501` and displays:
-  Incident metrics (total, critical, high, warning)
-  Detailed incident cards with RCA and recommendations
-  Trend visualization and severity distribution
-  Auto-refresh capability

## 📁 Project Structure

```
AWS_Cloud-Ops_Agent/
├── agents/                          # AI agents
│   ├── metrics_analysis_agent.py    # Analyzes metrics, assigns severity
│   ├── log_analysis_agent.py        # Detects error patterns
│   └── rca_agent.py                 # Root cause analysis
│
├── orchestrator/                    # Main coordinator
│   └── orchestrator.py              # Orchestrates agent workflow
│
├── tools/                           # Data fetching utilities
│   ├── cloudwatch_logs_tool.py      # Fetch CloudWatch logs
│   ├── cloudwatch_metrics_tool.py   # Fetch CloudWatch metrics
│   ├── data_preprocessor.py         # Token optimization (97% reduction)
│   └── thresholds_tool.py           # Threshold management
│
├── incidents/                       # Incident logging
│   └── incident_log.py              # JSONL logger with UUIDs
│
├── incident_logs/                   # Generated incident data
│   └── incident_<uuid>_<timestamp>/ # One directory per incident
│       ├── results.json             # UI-ready summary
│       ├── incident_analysis.jsonl  # Complete audit trail
│       ├── raw_cloudwatch_logs.json # Original log data
│       └── raw_cloudwatch_metrics.json # Original metric data
│
├── lambda-simulator/                # Test incident generator
│   ├── lambda_function.py           # Simulates e-commerce app
│   └── requirements.txt
│
├── tests/                           # Unit tests
│   ├── test_log_agent.py
│   ├── test_metrics_agent.py
│   ├── test_rca_agent.py
│   └── test_orchestrator.py
│
├── dashboard.py                     # Streamlit dashboard
├── start_incident_assistant.py      # Main entry point
├── thresholds.json                  # Metric thresholds
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## 🔧 Configuration

### Metric Thresholds (`thresholds.json`)

```json
{
  "CPUUtilization": {
    "critical": 85,
    "warning": 70,
    "ok": 50
  },
  "MemoryUsageMB": {
    "critical": 240,
    "warning": 200,
    "ok": 150
  },
  "OrderLatencyMS": {
    "critical": 1500,
    "warning": 1000,
    "ok": 500
  }
}
```

### Data Preprocessing

Control token optimization in `tools/data_preprocessor.py`:

```python
# Adjust sampling parameters
max_error_samples = 10      # Error/warning log samples
max_info_samples = 5        # Info log samples
max_metric_stats = 10       # Aggregated metric statistics
```

##  Dashboard Guide

### Installation

```bash
pip install -r dashboard_requirements.txt
# or
pip install streamlit pandas plotly
```

### Running the Dashboard

```bash
streamlit run dashboard.py
```

### Features

1. **Top Metrics Bar**
   - Total incidents count
   - Critical/High/Warning severity counts

2. **Incident Cards**
   - Expandable sections for each incident
   - Description and detected issues
   - Root cause analysis
   - Actionable recommendations

3. **Trend Visualization**
   - Severity distribution pie chart
   - Timeline of incidents
   - Statistical summaries

4. **Filters and Controls**
   - Time window selector (10-120 minutes)
   - Severity filters
   - Auto-refresh toggle
   - Manual refresh button

##  Demo / Hackathon Guide

###  Video Walkthrough

For a complete video demonstration, check out our [YouTube demo](https://www.youtube.com/watch?v=8-itfsCbIWY) showing the entire workflow in action.

### Pre-Demo Setup (5 minutes)

1. **Deploy Lambda Simulator** (generates test incidents)
   ```bash
   cd lambda-simulator
   zip -r ../lambda-simulator.zip .
   aws lambda create-function \
     --function-name incident-simulator \
     --runtime python3.11 \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://../lambda-simulator.zip \
     --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
     --timeout 30
   ```

2. **Generate Test Incidents**
   ```bash
   # Generate 3 scenarios (~15-25 logs)
   aws lambda invoke \
     --function-name incident-simulator \
     --payload '{}' \
     response.json
   
   # Wait 10 seconds for CloudWatch propagation
   sleep 10
   ```

3. **Run Analysis**
   ```bash
   python start_incident_assistant.py
   ```

4. **Start Dashboard**
   ```bash
   streamlit run dashboard.py
   ```

### Demo Script (2.5 minutes)

**Introduction (30 seconds):**
> "We built an AI-powered incident detection system for AWS. It monitors CloudWatch logs and metrics, then uses LLM agents to automatically detect incidents and perform root cause analysis."

**Live Demo (60 seconds):**
> "Let me generate some incident data from our simulated e-commerce service..."
> 
> [Invoke Lambda]
> 
> "Now the system will analyze the telemetry data..."
> 
> [Run start_incident_assistant.py]
> 
> "Notice it's fetching logs and metrics. Our preprocessing layer reduces 150,000 characters down to fit the LLM's token limit - that's 97% reduction!
> 
> The first agent analyzes metrics and detects critical severity. The second agent examines logs for error patterns. The third agent performs root cause analysis..."

**Results (60 seconds):**
> [Show Dashboard]
> 
> "Here's what the system found:
> - CPU at 92% (critical threshold: 85%)
> - Memory pressure at 280MB (threshold: 240MB)
> - Order latency spiked to 2,500ms
> - Multiple payment authorization failures
> 
> The RCA agent concluded: 'Upstream service degradation causing cascading failures.'
> 
> Recommendation: 'Investigate user-profile-service, consider circuit breaker, scale inventory service.'"

### Noteworthy mentions

 **Multi-agent architecture** - Specialized agents for metrics, logs, and RCA  
 **Token optimization** - 97% reduction while preserving insights  
 **Real-time monitoring** - Can run continuously in production  
 **Structured logging** - Complete audit trail in JSONL  
 **AWS native** - Uses CloudWatch Logs and Metrics  
 **AI-powered** - Local LLM for privacy (no data leaves your network)  
 **Extensible** - Easy to add new agents or data sources  

##  Testing

### Run Unit Tests

```bash
# Test individual agents
python -m pytest tests/test_metrics_agent.py
python -m pytest tests/test_log_agent.py
python -m pytest tests/test_rca_agent.py

# Test orchestrator
python -m pytest tests/test_orchestrator.py

# Run all tests
python -m pytest tests/
```

### Test Lambda Simulator Locally

```bash
cd lambda-simulator
python lambda_function.py
```

### Test Multi-Incident Analysis

```bash
python run_multi_incident_analysis.py
```

##  Troubleshooting

### Ollama Token Limit Warnings

**Problem:** `truncating input prompt limit=4096 prompt=45950`

**Solution:** This should be fixed with data preprocessing. If it persists:
- Check `data_preprocessor.py` settings
- Reduce Lambda scenario count
- Verify preprocessing is enabled

### No Incidents Detected

**Problem:** System fetches data but doesn't detect incidents

**Solutions:**
- Verify Lambda actually executed (check CloudWatch Logs)
- Wait 10-15 seconds for data propagation
- Check log group name in `.env`
- Lower thresholds in `thresholds.json`

### AWS Credentials Error

**Problem:** `botocore.exceptions.NoCredentialsError`

**Solutions:**
```bash
# Verify credentials
python check_credentials.py

# Re-configure AWS CLI
aws configure

# Check environment variables
echo $AWS_ACCESS_KEY_ID
```

### Dashboard Shows No Incidents

**Solutions:**
- Run `python start_incident_assistant.py` at least once
- Verify `incident_logs/` directory exists
- Click " Refresh Now" button
- Check file permissions

### Slow Analysis Performance

**Solutions:**
- Ensure Ollama is running locally (not remote)
- Verify `OLLAMA_HOST` environment variable
- Reduce time window from 10 to 5 minutes
- Check system resources (CPU/RAM)

##  Continuous Monitoring (Optional)

To run continuous monitoring instead of single execution:

### Option 1: Polling Script

```bash
# Create poll.py or use the provided one
python poll.py
```

### Option 2: Cron Job

```bash
# Add to crontab (runs every 5 minutes)
*/5 * * * * cd /path/to/AWS_Cloud-Ops_Agent && python start_incident_assistant.py
```

### Option 3: EventBridge Schedule

```bash
# Create EventBridge rule to invoke detection periodically
aws events put-rule \
  --name incident-detection-schedule \
  --schedule-expression "rate(5 minutes)"
```

##  Success Metrics

The system successfully:

 Detects incidents with 97% token reduction  
 Analyzes 7 metric types + log events  
 Generates RCA in 30-60 seconds  
 Creates structured audit trails with unique IDs  
 Provides actionable recommendations  
 Visualizes trends in interactive dashboard  
 Maintains data integrity with raw dumps  

##  Contributing

Contributions are welcome! Areas for improvement:

- Additional AI agents (cost analysis, anomaly detection)
- Support for more AWS services (RDS, DynamoDB, ECS)
- Enhanced dashboard features (alerts, exports)
- Integration with incident management tools (PagerDuty, ServiceNow)
- Machine learning for threshold tuning
- Multi-region support

##  License

This project is licensed under the MIT License - see the LICENSE file for details.

##  Acknowledgments

- Built with [Strands Agents](https://github.com/strands-ai/strands-agents) framework
- Powered by [Ollama](https://ollama.ai) and Llama 3.1
- Visualization with [Streamlit](https://streamlit.io) and [Plotly](https://plotly.com)
- Cloud monitoring via [AWS CloudWatch](https://aws.amazon.com/cloudwatch/)

##  Support

For issues, questions, or suggestions:

1. Check existing documentation in the repo
2. Review [Troubleshooting](#-troubleshooting) section
3. Open an issue on GitHub

---

**Built for AWS Hackathon 2025** 🚀

*Reducing Mean Time To Resolution (MTTR) from hours to minutes with AI-powered incident analysis using Amazon Q developer.*

