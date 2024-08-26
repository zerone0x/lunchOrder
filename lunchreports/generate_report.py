from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
import os
import logging  #noqa


# Generic pdf response populator. Takes a report title, a report template,
# and a dictionary of kwargs to pass to the template.
def populate_pdf_response(*, report_title, report_template, **kwargs):
  response = HttpResponse(content_type="application/pdf")
  response[
      "Content-Disposition"] = f'attachment; filename="{report_title}.pdf"'
  template_path = os.path.join(settings.BASE_DIR, report_template)
  html = render_to_string(
      template_path,
      {
          "title": report_title,
          "BASE_DIR": settings.BASE_DIR,
          **kwargs,
      },
  )
  html = f"""
    <style>
        body {{
            margin: auto;
            width: 90%;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        tr, td {{
            border: 1px solid #000;
            padding: 2px;
            text-align: center;
        }}

        th {{
            font-weight: bold;
            background-color: grey;
        }}

        .total-quantity-row {{
            font-weight: bold;
            background-color: #e0e0e0;
        }}
    </style>
    {html}
"""
  pisa.CreatePDF(html, dest=response)
  return response


