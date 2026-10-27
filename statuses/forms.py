from django import forms
from django.forms import modelformset_factory
from .models import DepartmentStatus

DepartmentStatusFormSet = modelformset_factory(
    DepartmentStatus,
    fields=('status', 'responsible', 'comment'),
    extra=0,
    can_delete=False,
    widgets={
        'status': forms.RadioSelect(),
        'responsible': forms.Select(attrs={'class': 'form-select'}),
        'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    },
)