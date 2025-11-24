import json
import logging
import random
import time
import boto3
import os
import datetime
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client("cloudwatch")


# ----------------------------------------------------------
# Helper: Generate IDs
# ----------------------------------------------------------
def generate_trace_data():
    return {
        "trace_id": str(uuid.uuid4()),
        "span_id": str(uuid.uuid4())[:16],
        "correlation_id": str(uuid.uuid4())[:12],
    }


# ----------------------------------------------------------
# Structured Logging Helper (AWS + K8s + Datadog Hybrid)
# ----------------------------------------------------------
def log_event(level, event, message, scenario="unknown", **kwargs):

    trace_data = generate_trace_data()

    log = {
        "ts": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "level": level,
        "event": event,
        "message": message,
        # Microservice metadata
        "service": "order-processing-service",
        "environment": "prod-us-east-1",
        "version": "v2.13.5-a93fbd2",
        "component": "order-pipeline",
        "scenario": scenario,
        # Identifiers
        "requestId": os.getenv("AWS_REQUEST_ID", "N/A"),
        **trace_data,
        # kube-like metadata
        "pod": f"order-processing-{random.randint(1,5)}",
        "node": f"ip-10-0-{random.randint(1,255)}-{random.randint(1,255)}",
        # Additional details
        "details": kwargs,
    }

    if level == "INFO":
        logger.info(json.dumps(log))
    elif level == "WARNING":
        logger.warning(json.dumps(log))
    elif level == "ERROR":
        logger.error(json.dumps(log))


# ----------------------------------------------------------
# Metric Publisher (scenario-aware)
# ----------------------------------------------------------
def publish_metric(name, value, scenario="unknown"):
    cloudwatch.put_metric_data(
        Namespace="Custom/EcommerceOrderPipeline",
        MetricData=[{"MetricName": name, "Unit": "None", "Value": value}],
    )
    log_event(
        "INFO",
        "MetricPublished",
        f"Published metric {name}={value}",
        scenario=scenario,
        metric=name,
        value=value,
    )


# ----------------------------------------------------------
# Main Lambda Handler
# ----------------------------------------------------------
def lambda_handler(event, context):
    """
    For hackathon demo:
    - Assume a bad 10-minute window where everything is degraded.
    - Generate a burst of 10 incident events per invocation.
    - All scenarios are warning/critical severity so the agents will flag incidents.
    """

    log_event(
        "INFO",
        "LambdaStart",
        "Order-processing Lambda invoked",
        scenario="incident_burst",
    )

    # Only incident-producing scenarios
    incident_scenarios = [
        simulate_minor_degradation,
        simulate_major_symptom,
    ]

    try:
        # Burst of 10 bad events in a single invoke
        for i in range(10):
            chosen = random.choice(incident_scenarios)
            log_event(
                "INFO",
                "ScenarioChosen",
                f"Running incident scenario: {chosen.__name__}",
                scenario="incident_burst",
                sequence=i + 1,
            )
            chosen()

        return {
            "statusCode": 200,
            "body": json.dumps({"status": "incident_burst_generated"}),
        }

    except Exception as e:
        log_event(
            "ERROR",
            "ScenarioProcessingIssue",
            "Observed unexpected behavior during incident scenario generation",
            error=str(e),
            scenario="incident_burst",
        )
        return {"statusCode": 500, "body": json.dumps({"status": "processing_issue"})}


# ----------------------------------------------------------
# 1️⃣ HEALTHY ORDERS (KEPT FOR REFERENCE, NOT USED IN INCIDENT MODE)
# ----------------------------------------------------------
def simulate_healthy_order():
    """
    Not used in the current incident-only mode, but kept so we don't break imports.
    """
    scenario = "healthy_order"

    order_id = random.randint(100000, 999999)
    user_id = random.randint(1000, 9000)

    delay = random.uniform(0.2, 0.9)
    time.sleep(delay)
    latency = int(delay * 1000)

    publish_metric("CPUUtilization", random.uniform(10, 35), scenario)
    publish_metric("MemoryUsageMB", random.uniform(70, 130), scenario)
    publish_metric("OrderLatencyMS", latency, scenario)

    log_event(
        "INFO",
        "OrderPipelineProgress",
        "Order pipeline completed in expected window",
        scenario=scenario,
        orderId=order_id,
        userId=user_id,
        latency_ms=latency,
        downstream_calls=["inventory-service", "payment-service", "shipping-service"],
    )


# ----------------------------------------------------------
# 2️⃣ MINOR DEGRADATION -> FORCED CRITICAL (latency, CPU, memory, retries)
# ----------------------------------------------------------
def simulate_minor_degradation():
    scenario = "minor_degradation_critical"

    # Force high latency (above crit 1500ms) and heavy retries
    delay = random.uniform(2.0, 3.0)  # 2000–3000ms
    time.sleep(delay)
    latency = int(delay * 1000)

    # Force CPU and Memory above crit thresholds
    publish_metric("CPUUtilization", random.uniform(88, 95), scenario)  # crit_avg = 85
    publish_metric(
        "MemoryUsageMB", random.uniform(250, 320), scenario
    )  # crit_avg = 240
    publish_metric("OrderLatencyMS", latency, scenario)  # crit_avg = 1500
    publish_metric("RetryCount", random.randint(4, 6), scenario)  # crit_avg = 3

    log_event(
        "WARNING",
        "UpstreamResponsiveness",
        "Upstream response duration far above normal profile",
        scenario=scenario,
        latency_ms=latency,
        downstream="user-profile-service",
        observedRetries=random.randint(4, 6),
    )


# ----------------------------------------------------------
# 3️⃣ MAJOR SYMPTOMS (NO DIRECT FAIL WORDS, BUT CLEARLY BAD)
# ----------------------------------------------------------
def simulate_major_symptom():
    """
    Randomly choose one of the symptom patterns, all tuned to be critical.
    """
    symptom_patterns = [
        heavy_payment_signal,
        inventory_slow_signal,
        shipping_slow_signal,
        memory_pressure_signal,
    ]
    chosen = random.choice(symptom_patterns)
    chosen()


def heavy_payment_signal():
    scenario = "payment_signal_critical"

    # Multiple inconsistent authorization patterns + high error rate
    for i in range(random.randint(3, 5)):
        log_event(
            "WARNING",
            "AuthorizationPatternShift",
            "Observed inconsistent authorization response pattern",
            scenario=scenario,
            provider="Stripe",
            attempt=i,
            responseCode=random.choice([202, 207, 299]),
        )

    # ErrorRate well above critical 0.05
    publish_metric("ErrorRate", random.uniform(0.2, 0.6), scenario)


def inventory_slow_signal():
    scenario = "inventory_latency_critical"

    # Make inventory DB latency clearly above crit 900ms
    delay = random.uniform(1.5, 3.0)  # 1500–3000ms
    time.sleep(delay)

    publish_metric("CPUUtilization", random.uniform(90, 97), scenario)  # crit
    publish_metric("InventoryDBLatencyMS", delay * 1000, scenario)  # crit

    log_event(
        "WARNING",
        "ReservationDurationShift",
        "Inventory reservation taking far longer than expected window",
        scenario=scenario,
        observedDurationMS=int(delay * 1000),
        downstream="inventory-service",
    )


def shipping_slow_signal():
    scenario = "shipping_sla_critical"

    # Force a large delay and multiple downstream timeouts
    delay = random.uniform(2.5, 4.5)
    time.sleep(delay)

    # DownstreamTimeouts above crit 2
    publish_metric("DownstreamTimeouts", random.randint(3, 5), scenario)

    log_event(
        "WARNING",
        "DownstreamResponsiveness",
        "Shipping workflow response severely exceeded SLA window",
        scenario=scenario,
        observedLatencyMS=int(delay * 1000),
        call="POST /createLabel",
    )


def memory_pressure_signal():
    scenario = "memory_pressure_critical"

    # Force memory above crit threshold (240MB)
    mem = random.uniform(260, 340)
    publish_metric("MemoryUsageMB", mem, scenario)

    log_event(
        "WARNING",
        "ResourceConsumptionShift",
        "Observed sustained elevated memory consumption during payload handling",
        scenario=scenario,
        memoryMB=mem,
        payloadSizeKB=random.randint(800, 2000),
    )
