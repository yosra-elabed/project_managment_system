from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from chatbot.vector_store import add_document

from .models import Project


@receiver(pre_save, sender=Project)
def detect_status_change(sender, instance, **kwargs):
    """Repère si le statut vient de passer à COMPLETED, avant que la nouvelle valeur n'écrase l'ancienne."""
    if not instance.pk:
        instance._just_completed = False
        return
    try:
        old = Project.objects.get(pk=instance.pk)
    except Project.DoesNotExist:
        instance._just_completed = False
        return

    instance._just_completed = (
        old.status != Project.Status.COMPLETED
        and instance.status == Project.Status.COMPLETED
    )


@receiver(post_save, sender=Project)
def archive_project_on_completion(sender, instance, created, **kwargs):
    if getattr(instance, '_just_completed', False):
        now = timezone.now()
        # .update() évite de redéclencher pre_save/post_save (pas de boucle infinie)
        Project.objects.filter(pk=instance.pk).update(
            
            is_archived=True,
            archived_at=now,
        )
        send_archive_notification_emails(instance)


def send_archive_notification_emails(project):
    """Récupère tous les users concernés par le projet (assignés à une tâche + le manager) et les notifie."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Users distincts ayant au moins une tâche sur ce projet
    assigned_user_ids = (
        project.tasks
        .values_list('assigned_to_id', flat=True)
        .distinct()
    )
    recipients = User.objects.filter(id__in=assigned_user_ids)

    # On ajoute le manager du projet s'il n'est pas déjà dans la liste
    recipient_emails = {u.email for u in recipients if u.email}
    if project.manager and project.manager.email:
        recipient_emails.add(project.manager.email)

    if not recipient_emails:
        return

    send_mail(
        subject=f"Projet « {project.name} » archivé",
        message=(
            f"Bonjour,\n\n"
            f"Le projet « {project.name} » a été marqué comme terminé "
            f"et est désormais archivé. Il n'est plus disponible dans la liste des projets.\n\n"
            f"Cordialement."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=list(recipient_emails),
        fail_silently=False,
    )
    
@receiver(post_save, sender=Project)
def index_project_description(sender, instance, **kwargs):
    if instance.description and instance.description.strip():
        add_document(
            doc_id=f"project_{instance.pk}",
            text=instance.description,
            metadata={"project_id": instance.pk, "source_type": "project_description"}
        )    