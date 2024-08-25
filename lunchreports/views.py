from django.shortcuts import get_object_or_404,render
from django.views import View
from .models import Student, Teacher, LunchItem, LunchItemOrder
from django.core.exceptions import ValidationError
from .generate_report import populate_pdf_response
from collections import defaultdict
from decimal import Decimal
import logging  #noqa
from django.http import Http404
from django.db.models import F, Value, Case, When, CharField, Sum, Prefetch
from .models import LunchItemOrder, LunchItem, Teacher, Student


def index(request):
  return render(request, 'index.html')


def _get_lunch_items_from_request(request):
  lunch_item_names = ",".join(request.GET.getlist('lunch_items'))
  lunch_item_names = lunch_item_names.split(",")
  lunch_item_model_list = list(
      LunchItem.objects.filter(name__in=lunch_item_names))
  if len(lunch_item_model_list) <= 0:
    return list(LunchItem.objects.all())
  return lunch_item_model_list

def _generate_title(lunch_items):
    """
    Generate the title for the combined lunch report.

    Args:
        lunch_items (list): A list of lunch items.
    
    Returns:
        str: The title for the combined lunch report.
    """
    names = [item.name for item in lunch_items]
    names_string = ' '.join(names)
    title = names_string + ' Report'
    return title


def _get_total_quantity(lunch_items):
    return {item.name: _calculate_total_quantity_for_lunch_item(item) for item in lunch_items}

def _get_grouped_orders(lunch_items):
    """
    Group the orders by teachers.

    Args:
        lunch_item_orders (list): A list of orders.
    
    Returns:
        dict: A dictionary where the keys are teacher names and the values are dictionaries containing the group quantity and customers.
    """
    return {item.name: _calculate_total_quantity_for_lunch_item(item) for item in lunch_items}
            

def _calculate_total_quantity_for_lunch_item(lunch_item):
    """
    Calculate the total quantity for a given lunch item.

    Args:
        lunch_item (LunchItem): The lunch item to calculate the total quantity for.
    
    Returns:
        int: The total quantity for the given lunch item.
    """
    total_quantity = LunchItemOrder.objects.filter(lunch_item=lunch_item).aggregate(total=Sum('quantity'))['total']
    return total_quantity or 0

def _get_all_students_for_teacher():
    """
    Retrieve all teachers and their associated students.
    
    Returns:
        dict: A dictionary where the keys are teacher names and the values are lists of student names associated with each teacher.
        '-': A list of student names without a teacher.
        teacher_student_data: A dictionary where the keys are teacher names and the values are lists of student names associated with each teacher.
    """
    teachers_with_students = Teacher.objects.prefetch_related(Prefetch('students')).all()
    teacher_student_data = {teacher.name: [student.name for student in teacher.students.all()] + [teacher.name] for teacher in teachers_with_students}

    students_without_teacher = Student.objects.filter(teacher__isnull=True)
    teacher_student_data['-'] = [student.name for student in students_without_teacher]
    return teacher_student_data

def _fetch_orders_details(lunch_item):
    """
    Fetch the orders grouped by teacher.

    Args:
        lunch_item (LunchItem): The lunch item to fetch orders for.
    
    Returns:
        QuerySet: A QuerySet of orders grouped by teacher.
    """
    return (
        LunchItemOrder.objects
        .filter(lunch_item=lunch_item)
        .prefetch_related('student', 'student__teacher', 'teacher')
        .annotate(
            customer=Case(
                When(student__isnull=False, then=F('student__name')),
                When(teacher__isnull=False, then=F('teacher__name')),
                output_field=CharField()
            ),
            teacher_name=Case(
                When(student__isnull=False, student__teacher__name__isnull=True, then=Value('-')),
                When(student__isnull=False, then=F('student__teacher__name')),
                When(teacher__isnull=False, then=F('teacher__name')),
                output_field=CharField()
            )
        )
        .values('customer', 'teacher_name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('teacher_name', 'customer')
    )

def _organize_orders_by_teacher(lunch_item_orders):
    """
    Group the orders by teachers.

    Args:
        lunch_item_orders (list): A list of orders.
    
    Returns:
        dict: A dictionary where the keys are teacher names and the values are dictionaries containing the group quantity and customers.
    """
    grouped_orders = {}
    for order in lunch_item_orders:
        teacher_name = order['teacher_name']
        if teacher_name not in grouped_orders:
            grouped_orders[teacher_name] = {'group_quantity': 0, 'customers': {}}
        
        grouped_orders[teacher_name]['group_quantity'] += order['total_quantity']
        grouped_orders[teacher_name]['customers'][order['customer']] = order['total_quantity']

    # Ensure '-' group is included at the end if it exists
    if '-' in grouped_orders:
        ordered_grouped = {k: v for k, v in grouped_orders.items() if k != '-'}
        ordered_grouped['-'] = grouped_orders['-']
    else:
        ordered_grouped = grouped_orders

    return ordered_grouped

def lunch_report(request):
    try:
        lunch_items = _get_lunch_items_from_request(request)
        total_quantity_of_all_lunch_item = _get_total_quantity(lunch_items)
        print('total_quantity_of_all_lunch_item-------------------', total_quantity_of_all_lunch_item)
        orders_detail = _get_grouped_orders(lunch_items)
        print('orders_detail-------------------', orders_detail)
        total_quantity_of_all_lunch_item = {
        item.name: _calculate_total_quantity_for_lunch_item(item) for item in lunch_items
    }
        orders_detail = {
            item.name: _organize_orders_by_teacher(_fetch_orders_details(item)) for item in lunch_items
        }

        return render(request, 'lunch_order_report.html', {
            'All_lunch_items': lunch_items,
            'title': 'Lunch Order Report',
            'total_quantity_of_all_lunch_item': total_quantity_of_all_lunch_item,
            'orders_detail': orders_detail,
        })
    except Exception as e:
        print(e)
    # return populate_pdf_response(
    #   report_title="Lunch Order Report by Item",
    #   report_template="lunchreports/templates/lunch_order_report.html",
    #   All_lunch_items=lunch_items,
    # total_quantity_of_all_lunch_item=total_quantity_of_all_lunch_item,
    # orders_detail=orders_detail,
    #   )



def combined_lunch_report(request):
    lunch_items = _get_lunch_items_from_request(request)
    title = _generate_title(lunch_items)
     # Use the helper function to get the list of lunch items
    total_quantity_of_all_lunch_item = {
        item.name: _calculate_total_quantity_for_lunch_item(item) for item in lunch_items
    }
    orders_detail = {
        item.name: _organize_orders_by_teacher(_fetch_orders_details(item)) for item in lunch_items
    }
    teacher_student_data = _get_all_students_for_teacher()
    print('teacher_student_data-------------------', teacher_student_data)
    print('orders_detail-------------------', orders_detail)
    print('total_quantity_of_all_lunch_item-------------------', total_quantity_of_all_lunch_item)
    return render(request, 'combined_order_report.html',{
        "title": title,
        "orders_detail": orders_detail,
        "total_quantity_of_all_lunch_item": total_quantity_of_all_lunch_item,
        "lunch_items": lunch_items,
        "teacher_student_data": teacher_student_data,
    })
    return populate_pdf_response(
      report_title="Combined Lunch Order Report",
      report_template="lunchreports/templates/combined_order_report.html")