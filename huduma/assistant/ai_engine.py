import json
import re
from dotenv import load_dotenv
#import anthropic
import os
import openai
from openai import OpenAI


#client=anthropic.Anthropic()
load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an AI assistant for Vunoh Global, a platform that helps Kenyan diaspora customers manage tasks back home.

Your job is to analyze a customer's plain-English request and return ONLY a valid JSON object — no prose, no markdown, no code fences.

Extract the following and return exactly this structure:
{
  "intent": "<one of: send_money | hire_service | verify_document | get_airport_transfer | check_status>",
  "entities": {
    "amount": "<numeric value as string or null>",
    "currency": "<KES, USD, GBP, EUR or null>",
    "recipient_name": "<name or null>",
    "recipient_relationship": "<mother, father, friend, etc. or null>",
    "location": "<city/area in Kenya or null>",
    "service_type": "<cleaner, lawyer, errand_runner, driver, etc. or null>",
    "document_type": "<land_title, national_id, certificate, passport, etc. or null>",
    "urgency": "<high | normal | low>",
    "scheduled_date": "<date string or null>",
    "notes": "<any other important details or null>"
  },
  "steps": [
    "<step 1>",
    "<step 2>",
    "<step 3>"
  ],
  "messages": {
    "whatsapp": "<conversational WhatsApp message, 2-4 lines, 1-2 emojis, includes task code placeholder {TASK_CODE}>",
    "email": {
      "subject": "<formal email subject>",
      "body": "<formal email body, structured, includes task code placeholder {TASK_CODE}>"
    },
    "sms": "<under 160 chars, includes {TASK_CODE}>"
  }
}

Rules:
- intent MUST be one of the five values listed
- urgency defaults to "normal" unless the customer says urgent/ASAP/emergency
- steps must be specific to the intent (3-6 steps)
- All three message formats must include {TASK_CODE} as a literal placeholder
- Return ONLY the JSON. No explanation, no markdown fences."""


def call_ai(user_request: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_request
                }
            ],
        )
    
        raw = response.choices[0].message.content.strip()


        # Strip any accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    
    except json.JSONDecodeError as e:
        print("JSON ERROR:", e)
        print("RAW RESPONSE:", raw)
        raise Exception("AI returned invalid JSON")

    except Exception as e:
        print("OPENAI ERROR:", str(e))
        raise


def calculate_risk_score(intent: str, entities: dict) -> tuple[int, str]:
    """
    Risk scoring logic grounded in Kenyan diaspora context.
    Score 0-100. Levels: Low (0-30), Medium (31-60), High (61-100).
    """
    score = 0

    # --- Base risk by intent ---
    base = {
        "send_money": 20,
        "verify_document": 25,
        "hire_service": 10,
        "get_airport_transfer": 8,
        "check_status": 0,
    }
    score += base.get(intent, 10)

    # --- Urgency modifier ---
    urgency = entities.get("urgency", "normal")
    if urgency == "high":
        score += 20
    elif urgency == "low":
        score -= 5

    # --- Amount-based risk (money transfers) ---
    if intent == "send_money":
        amount_str = entities.get("amount")
        if amount_str:
            try:
                amount = float(str(amount_str).replace(",", ""))
                currency = entities.get("currency", "KES")
                # Normalise to KES roughly
                if currency in ("USD",):
                    amount *= 130
                elif currency in ("GBP",):
                    amount *= 165
                elif currency in ("EUR",):
                    amount *= 140

                if amount >= 500_000:
                    score += 30
                elif amount >= 100_000:
                    score += 20
                elif amount >= 50_000:
                    score += 10
                elif amount >= 10_000:
                    score += 5
            except (ValueError, TypeError):
                score += 5  # unknown amount = slight risk

    # --- Unknown recipient increases risk ---
    if intent == "send_money":
        if not entities.get("recipient_name"):
            score += 15
        if not entities.get("recipient_relationship"):
            score += 5

    # --- Document type risk ---
    if intent == "verify_document":
        doc_type = entities.get("document_type", "")
        if doc_type in ("land_title", "title_deed"):
            score += 25  # land fraud is very common in Kenya
        elif doc_type in ("national_id", "passport"):
            score += 10
        elif doc_type in ("certificate",):
            score += 8

    # --- High-urgency + high-amount is a classic fraud signal ---
    if urgency == "high" and intent == "send_money":
        score += 10

    # Clamp to 0-100
    score = max(0, min(100, score))

    if score <= 30:
        level = "Low"
    elif score <= 60:
        level = "Medium"
    else:
        level = "High"

    return score, level


def assign_team(intent: str) -> str:
    mapping = {
        "send_money": "Finance",
        "verify_document": "Legal",
        "hire_service": "Operations",
        "get_airport_transfer": "Logistics",
        "check_status": "Support",
    }
    return mapping.get(intent, "Support")
