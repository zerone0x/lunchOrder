from django.shortcuts import render
from django.views import View
from .models import Student, Teacher, LunchItem, LunchItemOrder
from django.core.exceptions import ValidationError
from .generate_report import populate_pdf_response
from collections import defaultdict
from decimal import Decimal
import logging  #noqa
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

def generate_report_title(lunch_items):
    """
    Generate a report title based on the provided lunch items.
    
    :param lunch_items: List of LunchItem objects.
    :return: A string representing the report title.
    """
    names = ', '.join(item.name for item in lunch_items)
    return f'{names} Report'

def _calculate_lunch_item_total_quantity(lunch_item):
    """
    Calculate the total quantity ordered for a specific lunch item.
    
    :param lunch_item: A LunchItem object.
    :return: Total quantity ordered.
    """
    return LunchItemOrder.objects.filter(lunch_item=lunch_item).aggregate(total=Sum('quantity'))['total'] or 0

def _calculate_total_quantities(lunch_items):
    """
    Calculate total quantities for a list of lunch items.
    
    :param lunch_items: List of LunchItem objects.
    :return: Dictionary mapping item names to their total ordered quantities.
    """
    return {item.name: _calculate_lunch_item_total_quantity(item) for item in lunch_items}

def _fetch_lunch_item_order_details(lunch_item):
    """
    Fetch detailed order information for a given lunch item, grouped by teacher.
    
    :param lunch_item: A LunchItem object.
    :return: QuerySet of order details annotated with customer and teacher names.
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

def _group_orders_by_teacher(lunch_item_orders):
    """
    Group lunch item orders by teacher.
    
    :param lunch_item_orders: QuerySet of order details.
    :return: Dictionary grouping orders by teacher name.
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

def _get_orders_grouped_by_teacher(lunch_items):
    """
    Get orders grouped by teacher for each lunch item.
    
    :param lunch_items: List of LunchItem objects.
    :return: Dictionary mapping item names to grouped order details.
    """
    return {item.name: _group_orders_by_teacher(_fetch_lunch_item_order_details(item)) 
            for item in lunch_items}

def _get_students_grouped_by_teacher():
    """
    Retrieve a mapping of teachers to their associated students.
    
    :return: Dictionary mapping teacher names to lists of their students.
    """
    teachers_with_students = Teacher.objects.prefetch_related(Prefetch('students')).all()
    teacher_student_mapping = {teacher.name: [student.name for student in teacher.students.all()] + [teacher.name] for teacher in teachers_with_students}

    students_without_teacher = Student.objects.filter(teacher__isnull=True)
    teacher_student_mapping['-'] = [student.name for student in students_without_teacher]
    return teacher_student_mapping

def _prepare_lunch_report_data(request):
    """
    Prepare data required for generating lunch reports.
    
    :param request: HTTP request object.
    :return: Tuple containing lunch items, their total quantities, and order details.
    """
    lunch_items = _get_lunch_items_from_request(request)
    total_lunch_item_quantities = _calculate_total_quantities(lunch_items)
    orders_detail = _get_orders_grouped_by_teacher(lunch_items)
    return lunch_items, total_lunch_item_quantities, orders_detail

def lunch_report(request):
    """
    Generate and return a PDF response for the lunch order report.
    
    :param request: HTTP request object.
    :return: HTTP response with the generated PDF report.
    """
    try:
        lunch_items, total_lunch_item_quantities, orders_detail = _prepare_lunch_report_data(request)
        return populate_pdf_response(
            report_title="Lunch Order Report by Item",
            report_template="lunchreports/templates/lunch_order_report.html",
            lunch_items=lunch_items,
            total_lunch_item_quantities=total_lunch_item_quantities,
            orders_detail=orders_detail,
        )
    except Exception as e:
        logging.error(f"Error generating lunch report: {e}")
        return render(request, 'error_page.html', {"error": "An error occurred while generating the report."})

def combined_lunch_report(request):
    """
    Generate and return a PDF response for the combined lunch order report.
    
    :param request: HTTP request object.
    :return: HTTP response with the generated PDF report.
    """
    try:
        lunch_items, total_lunch_item_quantities, orders_detail = _prepare_lunch_report_data(request)
        title = generate_report_title(lunch_items)
        teacher_student_mapping = _get_students_grouped_by_teacher()

        return populate_pdf_response(
            report_title="Combined Lunch Order Report",
            report_template="lunchreports/templates/combined_order_report.html",
            title=title,
            orders_detail=orders_detail,
            total_lunch_item_quantities=total_lunch_item_quantities,
            lunch_items=lunch_items,
            teacher_student_mapping=teacher_student_mapping
        )
    except Exception as e:
        logging.error(f"Error generating combined lunch report: {e}")
        return render(request, 'error_page.html', {"error": "An error occurred while generating the report."})