from django.db import models

# Create your models here.
import uuid

def generate_task_code():
    return "VG-" + uuid.uuid4().hex[:8].upper()


class Task(models.Model):
    INTENT_CHOICES = [
        ("send_money", "Send Money"),
        ("hire_service", "Hire Service"),
        ("verify_document", "Verify Document"),
        ("get_airport_transfer", "Get Airport Transfer"),
        ("check_status", "Check Status"),
    ]
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]
    TEAM_CHOICES = [
        ("Finance", "Finance Team"),
        ("Operations", "Operations Team"),
        ("Legal", "Legal Team"),
        ("Logistics", "Logistics Team"),
        ("Support", "Support Team"),
    ]

    task_code = models.CharField(max_length=20, unique=True, default=generate_task_code)
    original_request = models.TextField()
    intent = models.CharField(max_length=50, choices=INTENT_CHOICES)
    entities = models.JSONField(default=dict)
    risk_score = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=10, default="Low")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    assigned_team = models.CharField(max_length=20, choices=TEAM_CHOICES, default="Support")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task_code} — {self.intent}"


class TaskStep(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="steps")
    step_number = models.IntegerField()
    description = models.TextField()
    is_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ["step_number"]


class TaskMessage(models.Model):
    CHANNEL_CHOICES = [
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="messages")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class StatusHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
