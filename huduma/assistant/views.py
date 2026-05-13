from django.shortcuts import render

# Create your views here.
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Task, TaskStep, TaskMessage, StatusHistory
from .ai_engine import call_ai, calculate_risk_score, assign_team


def dashboard(request):
    tasks = Task.objects.prefetch_related("steps", "messages", "status_history").all()
    return render(request, "assistant/dashboard.html", {"tasks": tasks})

@csrf_exempt
@require_http_methods(["POST"])
def submit_request(request):
    try:
        body = json.loads(request.body)
        user_request = body.get("request", "").strip()
        if not user_request:
            return JsonResponse({"error": "Request is empty."}, status=400)

        # 1. AI extraction
        ai_data = call_ai(user_request)

        intent = ai_data.get("intent", "check_status")
        entities = ai_data.get("entities", {})
        steps_list = ai_data.get("steps", [])
        messages_data = ai_data.get("messages", {})

        # 2. Risk scoring
        risk_score, risk_level = calculate_risk_score(intent, entities)

        # 3. Team assignment
        team = assign_team(intent)

        # 4. Create task
        task = Task.objects.create(
            original_request=user_request,
            intent=intent,
            entities=entities,
            risk_score=risk_score,
            risk_level=risk_level,
            assigned_team=team,
        )

        # 5. Create steps
        for i, step_desc in enumerate(steps_list, start=1):
            TaskStep.objects.create(task=task, step_number=i, description=step_desc)

        # 6. Create messages (replace placeholder with real task code)
        def inject_code(text):
            return text.replace("{TASK_CODE}", task.task_code)

        wa_body = inject_code(messages_data.get("whatsapp", ""))
        email_data = messages_data.get("email", {})
        email_subject = inject_code(email_data.get("subject", "Your Huduma Task"))
        email_body = inject_code(email_data.get("body", ""))
        sms_body = inject_code(messages_data.get("sms", ""))

        TaskMessage.objects.create(task=task, channel="whatsapp", body=wa_body)
        TaskMessage.objects.create(task=task, channel="email", subject=email_subject, body=email_body)
        TaskMessage.objects.create(task=task, channel="sms", body=sms_body)

        # Build response
        return JsonResponse({
            "task_code": task.task_code,
            "intent": task.intent,
            "entities": task.entities,
            "risk_score": task.risk_score,
            "risk_level": task.risk_level,
            "assigned_team": task.assigned_team,
            "status": task.status,
            "steps": [{"number": s.step_number, "description": s.description} for s in task.steps.all()],
            "messages": {
                "whatsapp": wa_body,
                "email": {"subject": email_subject, "body": email_body},
                "sms": sms_body,
            },
            "created_at": task.created_at.isoformat(),
        })

    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"AI returned unparseable response: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_status(request, task_id):
    try:
        body = json.loads(request.body)
        new_status = body.get("status")
        if new_status not in ["Pending", "In Progress", "Completed"]:
            return JsonResponse({"error": "Invalid status."}, status=400)

        task = Task.objects.get(pk=task_id)
        old_status = task.status
        if old_status != new_status:
            StatusHistory.objects.create(task=task, old_status=old_status, new_status=new_status)
            task.status = new_status
            task.save()

        return JsonResponse({"task_code": task.task_code, "status": task.status})
    except Task.DoesNotExist:
        return JsonResponse({"error": "Task not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_tasks(request):
    tasks = Task.objects.prefetch_related("steps", "messages").all()
    result = []
    for t in tasks:
        msgs = {m.channel: {"subject": m.subject, "body": m.body} for m in t.messages.all()}
        result.append({
            "id": t.id,
            "task_code": t.task_code,
            "intent": t.intent,
            "original_request": t.original_request,
            "entities": t.entities,
            "risk_score": t.risk_score,
            "risk_level": t.risk_level,
            "status": t.status,
            "assigned_team": t.assigned_team,
            "steps": [{"number": s.step_number, "description": s.description, "is_complete": s.is_complete}
                      for s in t.steps.all()],
            "messages": msgs,
            "created_at": t.created_at.isoformat(),
        })
    return JsonResponse({"tasks": result})
