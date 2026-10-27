from django.db import models
from accounts.models import User


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    message = models.TextField()       # ce que l'utilisateur a écrit
    response = models.TextField()      # ce que Claude a répondu
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} — {self.message[:50]}"