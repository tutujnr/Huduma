from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/submit/", views.submit_request, name="submit_request"),
    path("api/tasks/", views.get_tasks, name="get_tasks"),
    path("api/tasks/<int:task_id>/status/", views.update_status, name="update_status"),
]
