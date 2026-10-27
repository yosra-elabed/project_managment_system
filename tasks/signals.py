from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task
from chatbot.vector_store import add_document


@receiver(post_save, sender=Task)
def index_task_description(sender, instance, **kwargs):
    if instance.description and instance.description.strip():
        add_document(
            doc_id=f"task_{instance.pk}",
            text=instance.description,
            metadata={"project_id": instance.project_id, "source_type": "task_description"}
        )