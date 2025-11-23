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
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
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

    log_event("INFO", "LambdaStart", "Order-processing Lambda invoked")

    # Weighted realistic traffic mix
    scenario_weights = [
        (simulate_healthy_order, 0.70),
        (simulate_minor_degradation, 0.20),
        (simulate_major_symptom, 0.10),
    ]

    scenarios, weights = zip(*scenario_weights)
    chosen = random.choices(scenarios, weights=weights, k=1)[0]

    log_event("INFO", "ScenarioChosen", f"Running scenario: {chosen.__name__}")

    try:
        chosen()
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}

    except Exception as e:
        log_event(
            "ERROR",
            "ScenarioProcessingIssue",
            "Observed unexpected behavior during scenario",
            error=str(e),
        )
        return {"statusCode": 500, "body": json.dumps({"status": "processing_issue"})}


# ----------------------------------------------------------
# 1️⃣ HEALTHY ORDERS (MOST TRAFFIC)
# ----------------------------------------------------------
def simulate_healthy_order():
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
# 2️⃣ MINOR DEGREDATION (CACHE SLOW, RETRIES, ETC.)
# ----------------------------------------------------------
def simulate_minor_degradation():
    scenario = "minor_degradation"

    delay = random.uniform(1.0, 2.3)
    time.sleep(delay)
    latency = int(delay * 1000)

    publish_metric("CPUUtilization", random.uniform(40, 60), scenario)
    publish_metric("MemoryUsageMB", random.uniform(130, 200), scenario)
    publish_metric("OrderLatencyMS", latency, scenario)
    publish_metric("RetryCount", random.randint(1, 3), scenario)

    log_event(
        "WARNING",
        "UpstreamResponsiveness",
        "Upstream response duration exceeded normal profile",
        scenario=scenario,
        latency_ms=latency,
        downstream="user-profile-service",
        observedRetries=random.randint(1, 2),
    )


# ----------------------------------------------------------
# 3️⃣ MAJOR SYMPTOMS (NO DIRECT FAIL WORDS)
# ----------------------------------------------------------
def simulate_major_symptom():

    symptom_patterns = [
        heavy_payment_signal,
        inventory_slow_signal,
        shipping_slow_signal,
        memory_pressure_signal,
    ]
    chosen = random.choice(symptom_patterns)
    chosen()


def heavy_payment_signal():
    scenario = "payment_signal"

    for i in range(random.randint(2, 4)):
        log_event(
            "WARNING",
            "AuthorizationPatternShift",
            "Observed inconsistent authorization response pattern",
            scenario=scenario,
            provider="Stripe",
            attempt=i,
            responseCode=random.choice([202, 207, 299]),
        )

    publish_metric("ErrorRate", random.uniform(0.4, 0.9), scenario)


def inventory_slow_signal():
    scenario = "inventory_latency_signal"

    delay = random.uniform(1.8, 4.0)
    time.sleep(delay)

    publish_metric("CPUUtilization", random.uniform(65, 90), scenario)
    publish_metric("InventoryDBLatencyMS", delay * 1000, scenario)

    log_event(
        "WARNING",
        "ReservationDurationShift",
        "Inventory reservation observed longer-than-expected duration",
        scenario=scenario,
        observedDurationMS=int(delay * 1000),
        downstream="inventory-service",
    )


def shipping_slow_signal():
    scenario = "shipping_sla_shift"

    delay = random.uniform(2.5, 4.5)
    time.sleep(delay)

    publish_metric("DownstreamTimeouts", 1, scenario)

    log_event(
        "WARNING",
        "DownstreamResponsiveness",
        "Shipping workflow response exceeded expected SLA window",
        scenario=scenario,
        observedLatencyMS=int(delay * 1000),
        call="POST /createLabel",
    )


def memory_pressure_signal():
    scenario = "memory_pressure_signal"

    mem = random.uniform(220, 310)
    publish_metric("MemoryUsageMB", mem, scenario)

    log_event(
        "WARNING",
        "ResourceConsumptionShift",
        "Observed elevated memory consumption during payload handling",
        scenario=scenario,
        memoryMB=mem,
        payloadSizeKB=random.randint(500, 1500),
    )
