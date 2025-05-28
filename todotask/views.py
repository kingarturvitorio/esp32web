from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from .models import Todo
# Create your views here.

class TodoListView(ListView):
    model = Todo
    template_name = 'todo_list.html'
    context_object_name = 'todos'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['professional_todos'] = self.object_list.filter(category='professional')
        ctx['personal_todos'] = self.object_list.filter(category='personal')
        return ctx
    
class TodoCreateView(CreateView):
    model = Todo
    fields = ['title', 'assignee', 'category']
    template_name = 'todo_form.html'
    success_url = reverse_lazy('todo-list')

class TodoUpdateView(UpdateView):
    model = Todo
    fields = ['completed']
    template_name = 'todo_update.html'
    success_url = reverse_lazy('todo-list')