# Lambda Simulator

A Python-based AWS Lambda function that simulates various execution scenarios for CloudWatch monitoring and alerting demonstrations.

## Project Structure
```
lambda-simulator/
├── lambda_function.py    # Main Lambda function
├── requirements.txt      # Dependencies (none required)
└── README.md            # This file
```

## Simulation Scenarios

The function randomly selects one of these scenarios:

1. **Timeout** - Sleeps beyond limit, logs timeout error
2. **Slow Downstream** - Simulates 2-3s downstream call delay
3. **Retry Storm** - Logs connection reset errors 5-10 times
4. **Memory Spike** - Allocates large object, logs memory error
5. **Healthy Execution** - Normal successful execution

## Deployment Instructions

### 1. Create ZIP Package
```bash
cd lambda-simulator
zip -r lambda-simulator.zip .
```

### 2. Upload to AWS Lambda

#### Via AWS Console:
1. Go to AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. Function name: `incident-assistant-demo-func`
5. Runtime: `Python 3.11`
6. Click "Create function"
7. In "Code" section, click "Upload from" → ".zip file"
8. Upload `lambda-simulator.zip`

#### Via AWS CLI:
```bash
aws lambda create-function \
  --function-name incident-assistant-demo-func \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR-ACCOUNT:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda-simulator.zip
```

### 3. Configure Lambda Settings

#### Handler Configuration:
- Handler: `lambda_function.lambda_handler`

#### Timeout & Memory:
- Timeout: 5 seconds (to allow timeout simulation)
- Memory: 128 MB (sufficient for simulations)

#### Environment Variables (Optional):
- LOG_LEVEL: INFO

### 4. CloudWatch Logs Configuration

The function automatically logs to:
- Log Group: `/aws/lambda/incident-assistant-demo-func`
- Logs are created automatically when function runs

## EventBridge Schedule Setup

### Create EventBridge Rule (5-minute schedule):

#### Via AWS Console:
1. Go to Amazon EventBridge Console
2. Click "Create rule"
3. Name: `lambda-simulator-schedule`
4. Rule type: "Schedule"
5. Schedule pattern: "Rate expression"
6. Rate: `rate(5 minutes)`
7. Target: AWS Lambda function
8. Function: `incident-assistant-demo-func`
9. Click "Create rule"

#### Via AWS CLI:
```bash
# Create the rule
aws events put-rule \
  --name lambda-simulator-schedule \
  --schedule-expression "rate(5 minutes)"

# Add Lambda as target
aws events put-targets \
  --rule lambda-simulator-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:incident-assistant-demo-func"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name incident-assistant-demo-func \
  --statement-id allow-eventbridge \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:REGION:ACCOUNT:rule/lambda-simulator-schedule
```

## Testing

### Manual Test:
1. Go to Lambda Console
2. Select your function
3. Click "Test"
4. Create new test event (use default)
5. Click "Test"

### View Logs:
1. Go to CloudWatch Console
2. Navigate to "Log groups"
3. Find `/aws/lambda/incident-assistant-demo-func`
4. View log streams to see simulation outputs

## Cost Considerations

- Function uses minimal resources (128MB memory, <5s execution)
- Running every 5 minutes = ~8,640 invocations/month
- Well within AWS Free Tier limits (1M requests/month)
- CloudWatch Logs: First 5GB/month free

## Sample Log Outputs

```
[INFO] Lambda Simulator started
[INFO] Selected scenario: slow_downstream
[WARNING] Calling downstream service...
[WARNING] Downstream call took 2847 ms

[INFO] Lambda Simulator started  
[INFO] Selected scenario: retry_storm
[WARNING] Starting retry storm simulation with 7 retries
[ERROR] connection reset by peer
[ERROR] connection reset by peer
...
```