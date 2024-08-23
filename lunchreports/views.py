from django.shortcuts import render
from django.views import View
from .models import Student, Teacher, LunchItem, LunchItemOrder
from django.core.exceptions import ValidationError
from .generate_report import populate_pdf_response
from collections import defaultdict
from decimal import Decimal
import logging  #noqa


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


def lunch_report(request):
  lunch_item_model_list = _get_lunch_items_from_request(request)
  ###### TODO: Please implement ################################

  return populate_pdf_response(
      report_title="Lunch Order Report by Item",
      report_template="lunchreports/templates/lunch_order_report.html")


def combined_lunch_report(request):
  lunch_item_model_list = _get_lunch_items_from_request(request)
  ###### TODO: Please implement ################################

  return populate_pdf_response(
      report_title="Combined Lunch Order Report",
      report_template="lunchreports/templates/lunch_order_report.html")
