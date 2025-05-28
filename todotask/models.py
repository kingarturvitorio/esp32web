from django.db import models

# Create your models heres

class Todo(models.Model):

    CATEGORY_CHOICES = [
        ('professional', 'Profissional'),
        ('personal', 'Pessoal'),
    ]

    title = models.CharField('Título', max_length=500)
    assignee = models.CharField('Responsável', max_length=100)
    category = models.CharField('Categoria', max_length=12, choices=CATEGORY_CHOICES)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    completed = models.BooleanField('Concluído', default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"