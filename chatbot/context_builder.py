from django.utils import timezone
from chatbot.vector_store import search


def get_allowed_project_ids(user):
    from projects.models import Project

    if user.role == user.Role.ADMIN:
        # ✅ Admin : voit TOUT, y compris les projets archivés
        return list(Project.objects.all().values_list('id', flat=True))
    elif user.role == user.Role.PROJECT_MANAGER:
        # PM : garde le filtre is_archived=False, cohérent avec project_list
        return list(Project.objects.filter(manager=user, is_archived=False).values_list('id', flat=True))
    else:
        # User : idem
        return list(
            Project.objects.filter(tasks__assigned_to=user, is_archived=False)
            .distinct().values_list('id', flat=True)
        )
        


def build_user_context(user, user_question: str):
    from projects.models import Project
    from tasks.models import Task
    from statuses.models import DepartmentStatus

    project_ids = get_allowed_project_ids(user)
    projects = Project.objects.filter(id__in=project_ids).select_related('manager')
    today = timezone.now().date()

    structured_lines = [f"Date du jour: {today:%d/%m/%Y}\n"]

    for p in projects:
        structured_lines.append(
            f"### PROJET: {p.name} (ID {p.pk})\n"
            f"Statut d'avancement: {p.get_status_display()}\n"
            f"Client: {p.get_account_name_display()}\n"
            f"Manager: {p.manager}\n"
            f"Début: {p.start_date or '—'} | Fin: {p.end_date or '—'}"
        )

        dept_statuses = DepartmentStatus.objects.filter(project=p).select_related('responsible')
        if dept_statuses.exists():
            structured_lines.append("Statuts RAG par département:")
            for ds in dept_statuses:
                structured_lines.append(
                    f"  - {ds.get_department_display()}: {ds.get_status_display()} "
                    f"| Responsable: {ds.responsible or '—'} "
                    f"| Commentaire: {ds.comment or '—'}"
                )
        else:
            structured_lines.append("Statuts RAG par département: aucun renseigné.")

        if user.role == user.Role.USER:
            project_tasks = Task.objects.filter(project=p, assigned_to=user)
        else:
            project_tasks = Task.objects.filter(project=p).select_related('assigned_to')

        if project_tasks.exists():
            structured_lines.append("Tâches:")
            for t in project_tasks:
                is_overdue = (
                    t.due_date is not None
                    and t.due_date < today
                    and t.status != Task.Status.DONE
                )
                retard_label = " ⚠️ EN RETARD" if is_overdue else ""
                structured_lines.append(
                    f"  - « {t.title} » | Statut: {t.get_status_display()} | "
                    f"Assignée à: {t.assigned_to.username if t.assigned_to else 'Non assignée'} | "
                    f"Échéance: {t.due_date if t.due_date else 'Non définie'}{retard_label}"
                )

        structured_lines.append("")

    vector_results = search(user_question, allowed_project_ids=project_ids, top_k=5)
    vector_lines = [
        f"- ({r['metadata']['source_type']}, projet #{r['metadata']['project_id']}): {r['text']}"
        for r in vector_results
    ]

    context = "DONNÉES COMPLÈTES (projets, statuts RAG par département, tâches):\n" + "\n".join(structured_lines)
    if vector_lines:
        context += "\n\nEXTRAITS SÉMANTIQUEMENT PERTINENTS:\n" + "\n".join(vector_lines)

    return context if (len(structured_lines) > 1 or vector_lines) else "Aucune donnée accessible pour cet utilisateur."