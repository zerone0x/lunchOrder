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


def _calculate_total_quantity_for_lunch_item(lunch_item):
    total_quantity = LunchItemOrder.objects.filter(lunch_item=lunch_item).aggregate(total=Sum('quantity'))['total']
    return total_quantity or 0

def _get_all_students_for_teacher():
    """
    Retrieve all teachers and their associated students.
    
    Returns:
        dict: A dictionary where the keys are teacher names and the values are lists of student names associated with each teacher.
    """
    # TODO 加上老师 和 考虑没有老师的情况
    teachers_with_students = Teacher.objects.prefetch_related(Prefetch('students')).all()
    teacher_student_data = {teacher.name: [student.name for student in teacher.students.all()] for teacher in teachers_with_students}
    return teacher_student_data

def _fetch_orders_grouped_by_teacher(lunch_item):
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

def _get_grouped_orders(lunch_item_orders):
    grouped_orders = {}
    for order in lunch_item_orders:
        teacher_name = order['teacher_name']
        if teacher_name not in grouped_orders:
            grouped_orders[teacher_name] = {'group_quantity': 0, 'customers': []}
        
        grouped_orders[teacher_name]['group_quantity'] += order['total_quantity']
        grouped_orders[teacher_name]['customers'].append(order)

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
        each_total_quantity_of_all_lunch_item = {
            item.name: _calculate_total_quantity_for_lunch_item(item) for item in lunch_items
        }
        orders_detail = {
            item.name: _get_grouped_orders(_fetch_orders_grouped_by_teacher(item)) for item in lunch_items
        }
        print('orders_detail-------------------', orders_detail)

        return render(request, 'lunch_order_report.html', {
            'All_lunch_items': lunch_items,
            'title': 'Lunch Order Report',
            'each_total_quantity_of_all_lunch_item': each_total_quantity_of_all_lunch_item,
            'orders_detail': orders_detail,
        })
    except Exception as e:
        return render(request, 'error.html', {'error_message': str(e)})
    # return populate_pdf_response(
    #   report_title="Lunch Order Report by Item",
    #   report_template="lunchreports/templates/lunch_order_report.html",
    #   All_lunch_items=lunch_items,
    # each_total_quantity_of_all_lunch_item=each_total_quantity_of_all_lunch_item,
    # orders_detail=orders_detail,
    #   )


def combined_lunch_report(request):
    # Use the helper function to get the list of lunch items
    
    lunch_items = _get_lunch_items_from_request(request)
    # orders=_fetch_orders_grouped_by_teacher(lunch_items)
    # print('------orders', orders)
    names = [item.name for item in lunch_items]

# 将所有名称组合成一个字符串，使用逗号分隔
    names_string = ' '.join(names)

    print(names_string)
    report_data = {}
    lunch_obj = LunchItem.objects.all()

# Create the title by concatenating the string with ' report'
    title = names_string + ' Report'
    lunch_items = _get_lunch_items_from_request(request)
    each_total_quantity_of_all_lunch_item = {
        item.name: _calculate_total_quantity_for_lunch_item(item) for item in lunch_items
    }
    orders_detail = {
        item.name: _get_grouped_orders(_fetch_orders_grouped_by_teacher(item)) for item in lunch_items
    }
    teacher_student_data = _get_all_students_for_teacher()
    print('teacher_student_data-------------------', teacher_student_data)
    print('orders_detail-------------------', orders_detail)
    print('each_total_quantity_of_all_lunch_item-------------------', each_total_quantity_of_all_lunch_item)
    return render(request, 'combined_order_report.html',{
        "title": title,
        "orders_detail": orders_detail,
        "each_total_quantity_of_all_lunch_item": each_total_quantity_of_all_lunch_item,
        "lunch_items": lunch_items,
        "teacher_student_data": teacher_student_data,
    })



    # =========
    # =========
    # =========
    # =========
    # for item in lunch_items:
    #     # Get orders for the current lunch item
    #     lunch_item_orders = (
    #         LunchItemOrder.objects
    #         .filter(lunch_item=item)
    #         .values('teacher__name', 'student__name', 'quantity')
    #         .order_by('teacher__name', 'student__name')
    #     )

    #     for order in lunch_item_orders:
    #         teacher_name = order['teacher__name'] or '-'
    #         student_name = order['student__name'] or 'No Student'
    #         quantity = order['quantity']

    #         if teacher_name not in report_data:
    #             report_data[teacher_name] = {'students': {}, 'totals': {}}

    #         if student_name not in report_data[teacher_name]['students']:
    #             report_data[teacher_name]['students'][student_name] = {}

    #         # Update the quantity for the current lunch item
    #         if item.name not in report_data[teacher_name]['students'][student_name]:
    #             report_data[teacher_name]['students'][student_name][item.name] = 0
    #         report_data[teacher_name]['students'][student_name][item.name] += quantity

    #         # Update the total for the teacher group
    #         if item.name not in report_data[teacher_name]['totals']:
    #             report_data[teacher_name]['totals'][item.name] = 0
    #         report_data[teacher_name]['totals'][item.name] += quantity

    # # Calculate overall totals for each lunch item
    # overall_totals = {item.name: 0 for item in lunch_items}
    # for teacher_data in report_data.values():
    #     for item_name, total in teacher_data['totals'].items():
    #         overall_totals[item_name] += total
    # =========
    
    # Render the report using the specified template
    return populate_pdf_response(
      report_title="Combined Lunch Order Report",
      report_template="lunchreports/templates/combined_order_report.html")