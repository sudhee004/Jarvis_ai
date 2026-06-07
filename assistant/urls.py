"""
URL configuration for the assistant app — Day 7: Voice + Documents + Settings.
"""

from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    # ------------------------------------------------------------------ #
    # Public pages                                                         #
    # ------------------------------------------------------------------ #
    path('',        views.home,  name='home'),
    path('about/',  views.about, name='about'),

    # ------------------------------------------------------------------ #
    # Authentication                                                       #
    # ------------------------------------------------------------------ #
    path('register/', views.register_view, name='register'),
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),

    # ------------------------------------------------------------------ #
    # Protected pages                                                      #
    # ------------------------------------------------------------------ #
    path('dashboard/', views.dashboard, name='dashboard'),

    # ------------------------------------------------------------------ #
    # Chat system                                                          #
    # ------------------------------------------------------------------ #
    path('chat/',                             views.chat_home,    name='chat_home'),
    path('chat/new/',                         views.new_chat,     name='new_chat'),
    path('chat/<int:session_id>/',            views.chat_session, name='chat_session'),
    path('chat/<int:session_id>/send/',       views.send_message, name='send_message'),
    path('chat/<int:session_id>/delete/',     views.delete_chat,  name='delete_chat'),

    # ------------------------------------------------------------------ #
    # Memory system — Day 6                                               #
    # ------------------------------------------------------------------ #
    path('memory/',                           views.memory_list,   name='memory_list'),
    path('memory/<int:memory_id>/edit/',      views.memory_edit,   name='memory_edit'),
    path('memory/<int:memory_id>/delete/',    views.memory_delete, name='memory_delete'),

    # ------------------------------------------------------------------ #
    # Knowledge Vault — Day 7                                             #
    # ------------------------------------------------------------------ #
    path('documents/',                         views.document_list,   name='document_list'),
    path('documents/<int:doc_id>/ask/',        views.document_ask,    name='document_ask'),
    path('documents/<int:doc_id>/delete/',     views.document_delete, name='document_delete'),

    # ------------------------------------------------------------------ #
    # Voice Settings — Day 7                                              #
    # ------------------------------------------------------------------ #
    path('settings/voice/',                    views.voice_settings_view, name='voice_settings'),

    # ------------------------------------------------------------------ #
    # Voice Assistant Page — Day 7 Enhancement                            #
    # ------------------------------------------------------------------ #
    path('voice/',                             views.voice_assistant_view, name='voice_assistant'),
    path('voice/send/',                        views.voice_assistant_send, name='voice_assistant_send'),
]
