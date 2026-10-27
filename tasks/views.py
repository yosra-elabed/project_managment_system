from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import TaskForm
from .models import Task
from django.utils import timezone



@login_required
@login_required
def task_list(request):
    user = request.user

    if user.role == user.Role.PROJECT_MANAGER:
        tasks = Task.objects.select_related('project', 'assigned_to').filter(
            project__manager=user
        )
    elif user.role == user.Role.ADMIN:
        tasks = Task.objects.select_related('project', 'assigned_to').all()
    else:
        tasks = Task.objects.select_related('project', 'assigned_to').filter(
            assigned_to=user
        )

    today = timezone.now().date()

    in_progress_count = tasks.filter(status='IN_PROGRESS').count()
    done_count = tasks.filter(status='DONE').count()
    overdue_count = tasks.filter(
        due_date__lt=today
    ).exclude(status='DONE').count()

    return render(request, 'tasks/task_list.html', {
        'tasks': tasks,
        'in_progress_count': in_progress_count,
        'done_count': done_count,
        'overdue_count': overdue_count,
    })
@login_required
def task_create_view(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tâche créée avec succès.")
            return redirect('tasks:task_list')
    else:
        form = TaskForm()

    return render(request, 'tasks/task_form.html', {'form': form, 'title': 'Nouvelle Tâche'})


@login_required
def task_detail(request, pk):
    task = get_object_or_404(
        Task.objects.select_related('project', 'assigned_to'), pk=pk
    )
    return render(request, 'tasks/task_detail.html', {'task': task})


@login_required
def task_edit_view(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, "Tâche modifiée avec succès.")
            return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)

    return render(request, 'tasks/task_form.html', {
        'form': form,
        'task': task,
        'title': 'Modifier la Tâche',
    })


@login_required
def task_delete_view(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST':
        title = task.title
        task.delete()
        messages.success(request, f"Tâche « {title} » supprimée avec succès.")
        return redirect('tasks:task_list')

    return render(request, 'tasks/task_confirm_delete.html', {'task': task})