from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name',
            'project_class',
            'project_type',
            'account_name',
            'owner',
            'manager',
            'description',
            'targets',
            'status',
            'start_date',
            'end_date',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'targets': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_name': forms.Select(attrs={'class': 'form-select'}),
            'project_class': forms.Select(attrs={'class': 'form-select'}),
            'project_type': forms.Select(attrs={'class': 'form-select'}),
            'owner': forms.TextInput(attrs={'class': 'form-control'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
              'status': forms.RadioSelect(),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        
    def clean_status(self):
          status = self.cleaned_data.get('status')

          if status == Project.Status.COMPLETED and self.instance.pk:
            open_tasks = self.instance.tasks.exclude(status='DONE').count()
            if open_tasks > 0:
                raise forms.ValidationError(
                    f"Impossible de marquer ce projet comme terminé : "
                    f"{open_tasks} tâche(s) encore ouverte(s)."
                )
          return status