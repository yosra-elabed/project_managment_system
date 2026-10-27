from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect ,get_object_or_404
from .forms import ProjectForm
from .models import Project
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .models import Delegation
from projects.models import Project
from tasks.models import Task
from accounts.models import User
from django.utils import timezone
from django.db.models import Q


@login_required
def project_create_view(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form})



@login_required
def project_list(request):
    user = request.user

    if user.role == user.Role.ADMIN:
        # Admin → tous les projets (y compris archivés)
        projects = Project.objects.select_related('manager').all()
    elif user.role == user.Role.PROJECT_MANAGER:
        # PM → uniquement ses projets, non archivés
        projects = Project.objects.select_related('manager').filter(
            manager=user, is_archived=False
        )
    else:
        # User simple → projets où il a au moins une tâche, non archivés
        projects = Project.objects.select_related('manager').filter(
            tasks__assigned_to=user, is_archived=False
        ).distinct()

    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related( 'manager'), pk=pk
    )
    return render(request, 'projects/project_detail.html', {'project': project})


@login_required
def project_edit_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/project_form.html', {
        'form': form,
        'project': project,  # utile pour adapter le titre en édition
    })
    
 


def activate_delegation(delegation):
    """Transfère les tâches non terminées du délégant vers le deputy, sur ce projet."""
    Task.objects.filter(
        project=delegation.project,
        assigned_to=delegation.delegator,
    ).exclude(status=Task.Status.DONE).update(assigned_to=delegation.deputy)


def deactivate_delegation(delegation, restore_tasks=False):
    """Désactive la délégation. Optionnel: rendre les tâches au délégant."""
    delegation.is_active = False
    delegation.save(update_fields=['is_active'])
    if restore_tasks:
        Task.objects.filter(
            project=delegation.project,
            assigned_to=delegation.deputy,
        ).exclude(status=Task.Status.DONE).update(assigned_to=delegation.delegator)


@login_required
@login_required
def delegation_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)

    # Seul le manager du projet (ou un admin) peut déléguer
    if request.user != project.manager and request.user.role != User.Role.ADMIN:
        raise PermissionDenied

    if request.method == 'POST':
        deputy_id = request.POST.get('deputy')
        reason = request.POST.get('reason', '')
        start_date = request.POST.get('start_date') or timezone.now().date()
        end_date = request.POST.get('end_date') or None

        deputy = get_object_or_404(User, pk=deputy_id)

        # Désactive toute délégation active existante sur ce projet
        Delegation.objects.filter(project=project, is_active=True).update(is_active=False)

        delegation = Delegation.objects.create(
            delegator=project.manager,
            deputy=deputy,
            project=project,
            reason=reason,
            start_date=start_date,
            end_date=end_date,
        )
        activate_delegation(delegation)
        messages.success(request, f"Le projet a été délégué à {deputy.username}.")
        return redirect('projects:project_detail', pk=project.pk)

    eligible_deputies = User.objects.exclude(pk=project.manager_id)   # ← SEULE LIGNE MODIFIÉE
    return render(request, 'projects/delegation_form.html', {
        'project': project,
        'eligible_deputies': eligible_deputies,
    })


@login_required
def delegation_end(request, pk):
    delegation = get_object_or_404(Delegation, pk=pk)
    if request.user != delegation.delegator and request.user.role != User.Role.ADMIN:
        raise PermissionDenied
    deactivate_delegation(delegation, restore_tasks=True)
    messages.info(request, "La délégation a été terminée, le projet revient à son responsable initial.")
    return redirect('projects:project_detail', pk=delegation.project.pk)
@login_required
def delegation_list(request):
    user = request.user
    if user.role == User.Role.ADMIN or user.is_superuser:
        delegations = Delegation.objects.select_related('delegator', 'deputy', 'project').filter(is_active=True)
    else:
        delegations = Delegation.objects.select_related('delegator', 'deputy', 'project').filter(
            Q(delegator=user) | Q(deputy=user), is_active=True
        )
    return render(request, 'projects/delegation_list.html', {'delegations': delegations})
@login_required
def delegation_create_generic(request):
    user = request.user

    if user.role == User.Role.ADMIN or user.is_superuser:
        eligible_projects = Project.objects.filter(is_archived=False)
    else:
        eligible_projects = Project.objects.filter(manager=user, is_archived=False)

    if request.method == 'POST':
        project = get_object_or_404(Project, pk=request.POST.get('project'))

        if request.user != project.manager and request.user.role != User.Role.ADMIN:
            raise PermissionDenied

        deputy = get_object_or_404(User, pk=request.POST.get('deputy'))
        reason = request.POST.get('reason', '')
        start_date = request.POST.get('start_date') or timezone.now().date()
        end_date = request.POST.get('end_date') or None

        Delegation.objects.filter(project=project, is_active=True).update(is_active=False)

        delegation = Delegation.objects.create(
            delegator=project.manager,
            deputy=deputy,
            project=project,
            reason=reason,
            start_date=start_date,
            end_date=end_date,
        )
        activate_delegation(delegation)
        messages.success(request, f"Le projet « {project.name} » a été délégué à {deputy.username}.")
        return redirect('projects:delegation_list')

    eligible_deputies = User.objects.filter(role__in=[User.Role.PROJECT_MANAGER, User.Role.ADMIN])
    return render(request, 'projects/delegation_form_generic.html', {
        'eligible_projects': eligible_projects,
        'eligible_deputies': eligible_deputies,
    })