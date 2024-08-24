from django.db import models
from django.db.models import CheckConstraint, Q


class Teacher(models.Model):
  name = models.CharField(max_length=255)

  def __str__(self):
    return self.name


class Student(models.Model):
  name = models.CharField(max_length=255)
  teacher = models.ForeignKey(Teacher,
                              on_delete=models.SET_NULL,
                              null=True,
                              blank=True,
                              related_name="students")
  def __str__(self):
    return f"{self.name} - {self.teacher}"


# Represents an item that can be ordered (e.g. pizza, sandwich, water, cookie, etc.)
class LunchItem(models.Model):
  name = models.CharField(max_length=255, unique=True)

  def __str__(self):
    return self.name


# A lunch item order is made either by a student or a teacher, but not both.
# Note that a student/teacher can make multiple orders of the same item.
# For example, teacher1 orders 2 quantity of water, and then 1 quantity water later.
# These will be separate LunchItemOrder objects.
class LunchItemOrder(models.Model):
  student = models.ForeignKey(Student,
                              on_delete=models.PROTECT,
                              null=True,
                              blank=True)
  teacher = models.ForeignKey(Teacher,
                              on_delete=models.PROTECT,
                              null=True,
                              blank=True)
  lunch_item = models.ForeignKey(LunchItem,
                                 on_delete=models.PROTECT,
                                 related_name="lunch_item_orders")
  quantity = models.IntegerField(default=1)

  class Meta:
    constraints = [
        CheckConstraint(
            check=((Q(student__isnull=False) & Q(teacher__isnull=True)) |
                   (Q(student__isnull=True) & Q(teacher__isnull=False))),
            name='either_student_or_teacher_is_null_but_not_both'),
    ]

  def __str__(self):
    return f"{self.lunch_item} ({self.quantity}) - {self.student or self.teacher}"
