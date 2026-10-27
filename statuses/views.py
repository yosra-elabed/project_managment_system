from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from accounts.models import User
from projects.models import Project
from .forms import DepartmentStatusFormSet
from .models import DepartmentStatus, DepartmentStatusHistory
from django.contrib import messages
from django.core.exceptions import PermissionDenied



RAG_COLORS = {
    'RED': colors.HexColor('#e03131'),
    'ORANGE': colors.HexColor('#f08c00'),
    'GREEN': colors.HexColor('#2f9e44'),
}


@login_required
def project_status_view(request, pk):
    """Affiche et permet de modifier les statuts par département d'un projet.

    Avant chaque changement effectif (statut OU commentaire), une snapshot
    de l'ANCIEN état est enregistrée dans DepartmentStatusHistory, puis le
    nouvel état est appliqué sur DepartmentStatus.
    """

    project = get_object_or_404(Project, pk=pk)
    queryset = DepartmentStatus.objects.filter(project=project).order_by('department')

    if request.method == 'POST':
        formset = DepartmentStatusFormSet(request.POST, queryset=queryset)

        if formset.is_valid():
            # Requête SQL fraîche et indépendante -> snapshot fiable de l'état
            # AVANT modification (évite tout effet de bord avec le queryset
            # utilisé par le formset lui-même).
            old_values = {
                pk_: (status, comment)
                for pk_, status, comment in DepartmentStatus.objects
                    .filter(project=project)
                    .values_list('pk', 'status', 'comment')
            }

            for form in formset.forms:
                instance = form.instance
                if not instance.pk:
                    continue

                old_status, old_comment = old_values.get(instance.pk, (None, None))
                new_status = form.cleaned_data['status']
                new_comment = form.cleaned_data['comment']

                if (old_status, old_comment) != (new_status, new_comment):
                    DepartmentStatusHistory.objects.create(
                        department_status=instance,
                        status=old_status,
                        comment=old_comment,
                        changed_by=request.user,
                    )

                form.save()  # applique et persiste le nouvel état

            return redirect('statuses:project_status', pk=project.pk)
    else:
        formset = DepartmentStatusFormSet(queryset=queryset)

    forms_with_dept = list(zip(formset.forms, queryset))

    history = DepartmentStatusHistory.objects.filter(
        department_status__project=project
    ).select_related('department_status', 'changed_by').order_by('-changed_at')

    return render(request, 'statuses/project_status.html', {
        'project': project,
        'formset': formset,
        'forms_with_dept': forms_with_dept,
        'history': history,
    })


@login_required
def project_status_report_pdf(request, pk):
    """Génère et télécharge un rapport PDF : statuts actuels par département
    + historique complet des modifications (date de soumission + auteur)."""

    project = get_object_or_404(Project, pk=pk)
    dept_statuses = DepartmentStatus.objects.filter(
        project=project
    ).select_related('responsible').order_by('department')
    history = DepartmentStatusHistory.objects.filter(
        department_status__project=project
    ).select_related('department_status', 'changed_by').order_by('-changed_at')

    response = HttpResponse(content_type='application/pdf')
    filename = f"rapport_statuts_{project.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(
        response, pagesize=landscape(A4),
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title2', parent=styles['Title'],
        textColor=colors.HexColor('#0B2145'), fontSize=18,
    )
    subtitle_style = ParagraphStyle(
        'Sub2', parent=styles['Normal'],
        textColor=colors.HexColor('#6c7280'), fontSize=10,
    )
    section_style = ParagraphStyle(
        'Sec2', parent=styles['Heading2'],
        textColor=colors.HexColor('#0B2145'), fontSize=13,
        spaceBefore=16, spaceAfter=8,
    )

    author_name = request.user.get_full_name() or request.user.username

    story = [
        Paragraph(f"Rapport de statuts — {project.name}", title_style),
        Paragraph(
            f"Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')} par {author_name}",
            subtitle_style,
        ),
        Spacer(1, 12),
        Paragraph("Statuts actuels par département", section_style),
    ]

    # --- Tableau : statuts actuels ---
    current_data = [['Département', 'Statut', 'Responsable', 'Dernière mise à jour', 'Commentaire']]
    for ds in dept_statuses:
        current_data.append([
            ds.get_department_display(),
            ds.get_status_display(),
            ds.responsible.get_full_name() if ds.responsible and ds.responsible.get_full_name()
            else (ds.responsible.username if ds.responsible else '—'),
            ds.updated_at.strftime('%d/%m/%Y %H:%M'),
            Paragraph(ds.comment or '—', styles['Normal']),
        ])

    current_table = Table(
        current_data,
        colWidths=[35 * mm, 25 * mm, 40 * mm, 35 * mm, 70 * mm],
        repeatRows=1,
    )
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B2145')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e4e7ed')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fb')]),
    ]
    for i, ds in enumerate(dept_statuses, start=1):
        color = RAG_COLORS.get(ds.status)
        if color:
            style_cmds.append(('TEXTCOLOR', (1, i), (1, i), color))
            style_cmds.append(('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'))
    current_table.setStyle(TableStyle(style_cmds))
    story.append(current_table)
    story.append(Spacer(1, 18))

    # --- Tableau : historique ---
    story.append(Paragraph("Historique des modifications", section_style))
    if history:
        hist_data = [['Département', 'Statut (avant modif.)', 'Modifié par', 'Date de soumission', 'Commentaire']]
        for h in history:
            hist_data.append([
                h.department_status.get_department_display(),
                h.get_status_display(),
                h.changed_by.get_full_name() if h.changed_by and h.changed_by.get_full_name()
                else (h.changed_by.username if h.changed_by else '—'),
                h.changed_at.strftime('%d/%m/%Y %H:%M'),
                Paragraph(h.comment or '—', styles['Normal']),
            ])
        hist_table = Table(
            hist_data,
            colWidths=[35 * mm, 25 * mm, 40 * mm, 35 * mm, 70 * mm],
            repeatRows=1,
        )
        hist_style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B2145')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e4e7ed')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fb')]),
        ]
        for i, h in enumerate(history, start=1):
            color = RAG_COLORS.get(h.status)
            if color:
                hist_style_cmds.append(('TEXTCOLOR', (1, i), (1, i), color))
                hist_style_cmds.append(('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'))
        hist_table.setStyle(TableStyle(hist_style_cmds))
        story.append(hist_table)
    else:
        story.append(Paragraph("Aucun historique disponible.", styles['Normal']))

    doc.build(story)
    return response


@login_required
def department_status_history_pdf(request, history_pk):
    """Génère et télécharge un PDF pour UNE SEULE entrée d'historique
    (un snapshot précis), avec statut, date de soumission et auteur."""

    entry = get_object_or_404(
        DepartmentStatusHistory.objects.select_related(
            'department_status', 'department_status__project', 'changed_by'
        ),
        pk=history_pk,
    )
    project = entry.department_status.project

    response = HttpResponse(content_type='application/pdf')
    filename = (
        f"snapshot_{project.name.replace(' ', '_')}_"
        f"{entry.department_status.get_department_display().replace(' ', '_')}_"
        f"{entry.changed_at.strftime('%Y%m%d_%H%M')}.pdf"
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(
        response, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title3', parent=styles['Title'],
        textColor=colors.HexColor('#0B2145'), fontSize=17,
    )
    subtitle_style = ParagraphStyle(
        'Sub3', parent=styles['Normal'],
        textColor=colors.HexColor('#6c7280'), fontSize=10,
    )
    label_style = ParagraphStyle(
        'Label3', parent=styles['Normal'],
        textColor=colors.HexColor('#6c7280'), fontSize=9,
        fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=2,
    )
    value_style = ParagraphStyle(
        'Value3', parent=styles['Normal'],
        textColor=colors.HexColor('#1e2129'), fontSize=11.5,
    )

    author_name = entry.changed_by.get_full_name() if entry.changed_by and entry.changed_by.get_full_name() \
        else (entry.changed_by.username if entry.changed_by else '—')

    story = [
        Paragraph(f"Snapshot de statut — {project.name}", title_style),
        Paragraph(
            f"Document généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}",
            subtitle_style,
        ),
        Spacer(1, 14),
    ]

    data = [
        ['Département', entry.department_status.get_department_display()],
        ['Statut', entry.get_status_display()],
        ['Modifié par', author_name],
        ['Date de soumission', entry.changed_at.strftime('%d/%m/%Y à %H:%M')],
        ['Commentaire', entry.comment or '—'],
    ]

    color = RAG_COLORS.get(entry.status)

    table = Table(data, colWidths=[45 * mm, 110 * mm])
    style_cmds = [
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6c7280')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#e4e7ed')),
    ]
    if color:
        style_cmds.append(('TEXTCOLOR', (1, 1), (1, 1), color))
        style_cmds.append(('FONTNAME', (1, 1), (1, 1), 'Helvetica-Bold'))
    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    doc.build(story)
    return response
# statuses/views.py

@login_required
def status_report_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.user != project.manager and request.user.role != User.Role.ADMIN:
        raise PermissionDenied

    if request.method == 'POST':
        formset = DepartmentStatusFormSet(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.project = project
                instance.changed_by = request.user
                instance.is_released = False   # explicite : reste brouillon
                instance.save()
            messages.success(request, "Brouillon enregistré. N'oublie pas de le valider (Release).")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        formset = DepartmentStatusFormSet()

    return render(request, 'statuses/status_form.html', {
        'project': project,
        'formset': formset,
    })
    # statuses/views.py

@login_required
def release_status_report(request, pk):
    report = get_object_or_404(DepartmentStatusHistory, pk=pk)
    project = report.department_status.project

    # ✅ Seul PM (manager du projet) ou ADMIN peut valider
    if request.user != project.manager and request.user.role != User.Role.ADMIN:
        raise PermissionDenied

    if report.is_released:
        messages.warning(request, "Ce rapport est déjà validé.")
    else:
        report.is_released = True
        report.released_at = timezone.now()
        report.save(update_fields=['is_released', 'released_at'])
        messages.success(request, "Rapport validé avec succès.")

    return redirect('projects:project_detail', pk=project.pk)
# statuses/views.py

@login_required
def status_report_edit(request, pk):
    report = get_object_or_404(DepartmentStatusHistory, pk=pk)

    if report.is_released:
        messages.error(request, "Ce rapport est déjà validé et ne peut plus être modifié.")
        return redirect('projects:project_detail', pk=report.project.pk)

    # ... suite de la logique d'édition existante (formset, has_changed, etc.)