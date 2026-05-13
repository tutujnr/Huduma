from django.contrib import admin
from . models import *

# Register your models here.
admin.site.register(Task)
admin.site.register(TaskStep)
admin.site.register(TaskMessage)
admin.site.register(StatusHistory)
