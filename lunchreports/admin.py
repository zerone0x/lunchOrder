from django.contrib import admin

# Register your models here.
from .models import LunchItemOrder, LunchItem, Teacher, Student

class LunchItemOrderAdmin(admin.ModelAdmin):
  list_filter = ("lunch_item",)
admin.site.register(LunchItemOrder, LunchItemOrderAdmin)
admin.site.register(LunchItem)
admin.site.register(Teacher)
admin.site.register(Student)