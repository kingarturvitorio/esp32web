from django.urls import path
from .views import TodoListView, TodoCreateView, TodoUpdateView

urlpatterns = [
    path('todo/', TodoListView.as_view(), name='todo-list'),
    path('add/', TodoCreateView.as_view(), name='todo-add'),
    path('complete/<int:pk>/', TodoUpdateView.as_view(), name='todo-complete'),
]
