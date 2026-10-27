from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.utils import timezone

from accounts.models import User
from projects.models import Project
from tasks.models import Task


def pct(count, total):
    """Retourne un pourcentage arrondi, sans division par zéro."""
    return round((count / total) * 100) if total else 0


def get_contributor_ids(projects):
    return (
        Task.objects.filter(project__in=projects)
        .values_list('assigned_to_id', flat=True)
        .distinct()
    )


def compute_project_stats(projects):
    """Répartition par statut + RAG pour un queryset de projets."""
    total = projects.count()

    status_counts = {row['status']: row['count'] for row in projects.values('status').annotate(count=Count('id'))}
    project_stats = {
        'not_started': status_counts.get(Project.Status.NOT_STARTED, 0),
        'in_progress': status_counts.get(Project.Status.IN_PROGRESS, 0),
        'on_hold': status_counts.get(Project.Status.ON_HOLD, 0),
        'completed': status_counts.get(Project.Status.COMPLETED, 0),
        'cancelled': status_counts.get(Project.Status.CANCELLED, 0),
    }
    project_pct = {k: pct(v, total) for k, v in project_stats.items()}

    # RAG est une property -> calcul en Python
    rag_counts = {'RED': 0, 'ORANGE': 0, 'GREEN': 0, 'NONE': 0}
    for p in projects:
        rag = p.global_rag_status or 'NONE'
        rag_counts[rag] = rag_counts.get(rag, 0) + 1
    rag_pct = {k: pct(v, total) for k, v in rag_counts.items()}

    return {
        'total_projects': total,
        'project_stats': project_stats,
        'project_pct': project_pct,
        'rag_counts': rag_counts,
        'rag_pct': rag_pct,
    }


def compute_task_stats(tasks):
    """Répartition par statut + tâches en retard pour un queryset de tâches."""
    total = tasks.count()
    today = timezone.now().date()

    status_counts = {row['status']: row['count'] for row in tasks.values('status').annotate(count=Count('id'))}
    task_stats = {
        'todo': status_counts.get(Task.Status.TODO, 0),
        'in_progress': status_counts.get(Task.Status.IN_PROGRESS, 0),
        'done': status_counts.get(Task.Status.DONE, 0),
        'extra': status_counts.get(Task.Status.EXTRA, 0),
    }
    task_pct = {k: pct(v, total) for k, v in task_stats.items()}

    overdue_tasks = tasks.filter(due_date__lt=today).exclude(status=Task.Status.DONE)

    return {
        'total_tasks': total,
        'task_stats': task_stats,
        'task_pct': task_pct,
        'overdue_count': overdue_tasks.count(),
        'overdue_tasks': overdue_tasks.select_related('project', 'assigned_to').order_by('due_date')[:5],
    }


@login_required
def dashboard_view(request):
    """Vue générique qui redirige la logique vers le bon contenu selon le rôle."""
    user = request.user

    if user.role == User.Role.ADMIN or user.is_superuser:
        return admin_dashboard(request)
    elif user.role == User.Role.PROJECT_MANAGER:
        return pm_dashboard(request)
    else:
        return user_dashboard(request)


@login_required
def admin_dashboard(request):
    if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
        raise PermissionDenied

    projects = Project.objects.all()
    tasks = Task.objects.select_related('project', 'assigned_to')

    context = {
        'user': request.user,
        'total_users': User.objects.count(),
        'total_admins': User.objects.filter(role=User.Role.ADMIN).count(),
        'total_pms': User.objects.filter(role=User.Role.PROJECT_MANAGER).count(),
        'total_regular_users': User.objects.filter(role=User.Role.USER).count(),
        'projects': projects,
        'recent_tasks': tasks.order_by('-created_at')[:5],
    }
    context.update(compute_project_stats(projects))
    context.update(compute_task_stats(tasks))
    return render(request, 'dashboards/admin_dashboard.html', context)


@login_required
def pm_dashboard(request):
    if request.user.role != User.Role.PROJECT_MANAGER:
        raise PermissionDenied

    user = request.user
    projects = Project.objects.filter(manager=user)
    contributor_ids = get_contributor_ids(projects)
    contributors = User.objects.filter(id__in=contributor_ids)
    tasks = Task.objects.filter(project__in=projects).select_related('project', 'assigned_to')

    context = {
        'user': user,
        'projects': projects,
        'total_contributors': contributors.count(),
        'recent_tasks': tasks.order_by('-created_at')[:5],
        'contributors': contributors,
    }
    context.update(compute_project_stats(projects))
    context.update(compute_task_stats(tasks))
    return render(request, 'dashboards/pm_dashboard.html', context)


@login_required
def user_dashboard(request):
    if request.user.role != User.Role.USER:
        raise PermissionDenied

    user = request.user
    my_tasks = Task.objects.filter(assigned_to=user).select_related('project')
    project_ids = my_tasks.values_list('project_id', flat=True).distinct()
    my_projects = Project.objects.filter(id__in=project_ids)

    context = {
        'user': user,
        'projects': my_projects,                                    # ✅ renommé
        'recent_tasks': my_tasks.order_by('-created_at')[:5],       # ✅ renommé + tri cohérent
        'my_tasks': my_tasks.order_by('due_date'),                  # gardé si utilisé ailleurs dans le template
        'my_projects': my_projects,                                  # gardé si utilisé ailleurs dans le template
    }
    context.update(compute_project_stats(my_projects))
    context.update(compute_task_stats(my_tasks))
    return render(request, 'dashboards/user_dashboard.html', context)