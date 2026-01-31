import os

from django.forms.widgets import ClearableFileInput
from django.utils.html import conditional_escape, format_html

# class FilenameOnlyClearableFileInput(ClearableFileInput):
#     def format_value(self, value):
#         if value and hasattr(value, "name"):
#             return os.path.basename(value.name)
#         return super().format_value(value)

#     def get_context(self, name, value, attrs):
#         context = super().get_context(name, value, attrs)

#         if value and hasattr(value, "name"):
#             context["widget"]["value"] = os.path.basename(value.name)

#         return context

# /home/jelite/Devel/emarches/base/templates/base/widgets

class FilenameOnlyClearableFileInput(ClearableFileInput):
    template_name = "base/widgets/fnoc_file_input.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value and hasattr(value, "name"):
            context["filename"] = os.path.basename(value.name)
        return context