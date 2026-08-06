import json
import os
import re
import time

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
LIMITS = {"name": 120, "email": 254, "phone": 40, "message": 3000}


def response(status, message):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps({"message": message}),
    }


def clean(value):
    return value.strip() if isinstance(value, str) else ""


def validate(payload, now_ms=None):
    if not isinstance(payload, dict):
        return None, "Invalid request."
    if clean(payload.get("website")):
        return None, "Thanks — your message has been sent."

    values = {field: clean(payload.get(field)) for field in LIMITS}
    for field, maximum in LIMITS.items():
        if len(values[field]) > maximum:
            return None, "One or more fields are too long."
    if not values["name"] or not values["email"] or not values["message"]:
        return None, "Name, email and message are required."
    if not EMAIL_RE.fullmatch(values["email"]):
        return None, "Enter a valid email address."
    if "\r" in values["email"] or "\n" in values["email"]:
        return None, "Enter a valid email address."

    try:
        started_at = int(payload.get("startedAt", 0))
    except (TypeError, ValueError):
        started_at = 0
    current = now_ms if now_ms is not None else int(time.time() * 1000)
    if started_at <= 0 or current - started_at < 2500 or current - started_at > 86_400_000:
        return None, "Please reload the page and try again."
    return values, None


def send_email(values):
    import boto3

    destination = os.environ["CONTACT_TO_EMAIL"]
    source = os.environ["CONTACT_FROM_EMAIL"]
    phone = values["phone"] or "Not supplied"
    body = (
        f"Name: {values['name']}\n"
        f"Email: {values['email']}\n"
        f"Phone: {phone}\n\n"
        f"Message:\n{values['message']}"
    )
    boto3.client("sesv2").send_email(
        FromEmailAddress=source,
        Destination={"ToAddresses": [destination]},
        ReplyToAddresses=[values["email"]],
        Content={"Simple": {
            "Subject": {"Data": f"GOSBLO website enquiry from {values['name']}", "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
        }},
    )


def handler(event, _context):
    try:
        if event.get("requestContext", {}).get("http", {}).get("method") != "POST":
            return response(405, "Method not allowed.")
        raw_body = event.get("body") or ""
        if len(raw_body.encode("utf-8")) > 8_192:
            return response(413, "Request is too large.")
        payload = json.loads(raw_body)
        values, error = validate(payload)
        if error:
            status = 200 if clean(payload.get("website")) else 400
            return response(status, error)
        send_email(values)
        return response(200, "Thanks — your message has been sent.")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return response(400, "Invalid request.")
    except Exception as error:
        print(f"contact_delivery_failed type={type(error).__name__}")
        return response(503, "Message could not be sent. Please try again later.")
