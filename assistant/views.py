"""
Views for the assistant app — Day 6: Memory System.

Implements:
  - home          : Public landing page
  - about         : About page
  - register_view : User registration with form validation
  - login_view    : User login with Remember Me support
  - logout_view   : User logout with success message
  - dashboard     : Protected dashboard page (with memory stats)
  - chat_home     : Chat landing — redirect to latest session or empty state
  - new_chat      : Create a new ChatSession and redirect to it  (POST)
  - chat_session  : Load a specific session with all its messages (GET)
  - send_message  : AJAX — save user msg + real AI reply + memory extraction (POST)
  - delete_chat   : Soft-delete (archive) a ChatSession (POST, returns JSON)
  - memory_list   : List / add user memories  (GET + POST)
  - memory_edit   : Edit a single memory      (GET + POST)
  - memory_delete : Delete a memory           (POST)
"""

import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm, UserMemoryForm
from .models import ChatMessage, ChatSession, UserMemory
from .ai_service import generate_ai_response


# ---------------------------------------------------------------------------
# Shared feature list
# ---------------------------------------------------------------------------
FEATURES = [
    {
        'icon': 'bi-chat-dots-fill',
        'title': 'AI Chat',
        'description': (
            'Engage in natural, intelligent conversations. '
            'Jarvis understands context and provides smart, '
            'accurate responses tailored to your needs.'
        ),
        'color': 'feature-blue',
    },
    {
        'icon': 'bi-mic-fill',
        'title': 'Voice Assistant',
        'description': (
            'Hands-free control at your command. Speak naturally '
            'and let Jarvis handle tasks, answer questions, and '
            'manage your schedule effortlessly.'
        ),
        'color': 'feature-purple',
    },
    {
        'icon': 'bi-journal-bookmark-fill',
        'title': 'Notes & Reminders',
        'description': (
            'Never forget what matters. Jarvis captures your ideas, '
            'sets smart reminders, and organises everything so you '
            "can focus on what's important."
        ),
        'color': 'feature-teal',
    },
    {
        'icon': 'bi-brain',
        'title': 'Personal Memory',
        'description': (
            'Jarvis learns and remembers. Your preferences, history, '
            'and context are stored securely, making every interaction '
            'smarter than the last.'
        ),
        'color': 'feature-orange',
    },
]


# ===========================================================================
# Public pages
# ===========================================================================

def home(request):
    """Public landing page — features grid + hero CTA."""
    return render(request, 'assistant/home.html', {
        'page_title': 'Jarvis AI Assistant — Your Personal AI Productivity Partner',
        'features': FEATURES,
    })


def about(request):
    """About page with project overview."""
    return render(request, 'assistant/about.html', {
        'page_title': 'About — Jarvis AI Assistant',
    })


# ===========================================================================
# Authentication
# ===========================================================================

def register_view(request):
    """
    User registration.
    GET  → blank form
    POST → validate, create user, auto-login, redirect to dashboard
    """
    if request.user.is_authenticated:
        return redirect('assistant:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f'Welcome to Jarvis, {user.username}! '
                f'Your account has been created successfully.'
            )
            return redirect('assistant:dashboard')
        else:
            messages.error(request, 'Please correct the errors below and try again.')
    else:
        form = RegisterForm()

    return render(request, 'assistant/register.html', {
        'page_title': 'Create Account — Jarvis AI Assistant',
        'form': form,
    })


def login_view(request):
    """
    User login.
    GET  → blank form
    POST → validate, set session expiry, redirect to dashboard
    """
    if request.user.is_authenticated:
        return redirect('assistant:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            remember_me = form.cleaned_data.get('remember_me', False)
            login(request, user)
            request.session.set_expiry(60 * 60 * 24 * 30 if remember_me else 0)
            messages.success(request, f'Welcome back, {user.username}! You are now logged in.')
            next_url = request.GET.get('next', '')
            return redirect(next_url or 'assistant:dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = LoginForm(request)

    return render(request, 'assistant/login.html', {
        'page_title': 'Login — Jarvis AI Assistant',
        'form': form,
    })


def logout_view(request):
    """Log the current user out and redirect to homepage."""
    username = request.user.username if request.user.is_authenticated else ''
    logout(request)
    if username:
        messages.info(request, f'Goodbye, {username}! You have been logged out successfully.')
    return redirect('assistant:home')


# ===========================================================================
# Dashboard
# ===========================================================================

@login_required(login_url='/login/')
def dashboard(request):
    """Protected dashboard with stats, quick-actions, account info, and memory count."""
    memory_count = UserMemory.objects.filter(user=request.user, is_active=True).count()
    context = {
        'page_title': f'Dashboard — {request.user.username} | Jarvis AI',
        'user': request.user,
        'stats': [
            {'label': 'Conversations',  'value': ChatSession.objects.filter(user=request.user, status='active').count(),
             'icon': 'bi-chat-dots-fill',       'color': 'stat-blue'},
            {'label': 'Memories Saved', 'value': memory_count,
             'icon': 'bi-brain',                'color': 'stat-teal'},
            {'label': 'Reminders Set',  'value': '0',
             'icon': 'bi-bell-fill',             'color': 'stat-purple'},
            {'label': 'Tasks Done',     'value': '0',
             'icon': 'bi-check-circle-fill',     'color': 'stat-orange'},
        ],
        'quick_actions': [
            {'label': 'Start AI Chat',   'icon': 'bi-chat-dots',    'color': 'qa-blue',   'href': '/chat/'},
            {'label': 'My Memories',     'icon': 'bi-brain',        'color': 'qa-teal',   'href': '/memory/'},
            {'label': 'Voice Assistant', 'icon': 'bi-mic',          'color': 'qa-purple', 'href': '#'},
            {'label': 'Add Reminder',    'icon': 'bi-bell-plus',    'color': 'qa-orange', 'href': '#'},
        ],
    }
    return render(request, 'assistant/dashboard.html', context)


# ===========================================================================
# Chat System — Sprint 3
# ===========================================================================

def _get_user_sessions(user):
    """Return all active ChatSessions for `user`, newest first."""
    return ChatSession.objects.filter(
        user=user, status='active'
    ).order_by('-last_message_at', '-created_at')


@login_required(login_url='/login/')
def chat_home(request):
    """
    Chat landing.
    Redirects to the most recent active session if one exists,
    otherwise renders the empty-state chat page.
    """
    sessions = _get_user_sessions(request.user)
    latest   = sessions.first()
    if latest:
        return redirect('assistant:chat_session', session_id=latest.id)

    return render(request, 'assistant/chat.html', {
        'page_title':     'Chat — Jarvis AI Assistant',
        'sessions':       sessions,
        'active_session': None,
        'chat_messages':  [],
    })


@login_required(login_url='/login/')
@require_POST
def new_chat(request):
    """
    Create a new ChatSession (POST only) and redirect to it.
    Accepts an optional 'title' field in POST data.
    """
    title   = request.POST.get('title', '').strip() or 'New Conversation'
    session = ChatSession.objects.create(
        user=request.user,
        title=title,
        last_message_at=timezone.now(),
    )
    return redirect('assistant:chat_session', session_id=session.id)


@login_required(login_url='/login/')
def chat_session(request, session_id):
    """
    Load a specific ChatSession and all its messages (oldest → newest).
    Returns 404 if the session doesn't belong to the logged-in user.
    """
    session       = get_object_or_404(ChatSession, id=session_id, user=request.user)
    sessions      = _get_user_sessions(request.user)
    chat_messages = session.messages.order_by('created_at')

    return render(request, 'assistant/chat.html', {
        'page_title':     f'{session.title} — Jarvis AI',
        'sessions':       sessions,
        'active_session': session,
        'chat_messages':  chat_messages,
    })


@login_required(login_url='/login/')
@require_POST
def send_message(request, session_id):
    """
    AJAX endpoint — persist a user message and return a placeholder AI reply.

    Expected: JSON body  { "content": "..." }
              or form    content=...
    Returns:  JSON       { "status": "ok", "user_message": {...}, "ai_message": {...} }
    """
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    # Accept JSON body or form-encoded data
    try:
        body    = json.loads(request.body)
        content = body.get('content', '').strip()
    except (json.JSONDecodeError, AttributeError):
        content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse(
            {'status': 'error', 'message': 'Message content is required.'},
            status=400,
        )

    # --- Persist user message ---
    user_msg = ChatMessage.objects.create(
        session=session,
        role='user',
        content=content,
    )

    # --- Build conversation history for context ---
    prior_messages = list(
        session.messages
        .exclude(pk=user_msg.pk)
        .order_by('created_at')
        .values('role', 'content')
    )
    history = [
        {'role': msg['role'], 'content': msg['content']}
        for msg in prior_messages
        if msg['role'] in ('user', 'assistant')
    ]

    # --- Generate real AI response (with user memories injected into prompt) ---
    ai_reply = generate_ai_response(
        user_message=content,
        history=history,
        user=request.user,          # <-- enables memory-aware responses
    )

    ai_msg = ChatMessage.objects.create(
        session=session,
        role='assistant',
        content=ai_reply,
    )

    # --- Extract and save memories from user's message (non-blocking) ---
    try:
        from .memory_service import extract_and_save_memories
        extract_and_save_memories(
            user=request.user,
            user_message=content,
            session=session,
        )
    except Exception as mem_exc:
        import logging
        logging.getLogger(__name__).warning("Memory extraction skipped: %s", mem_exc)

    # --- Update session metadata ---
    word_count = len(content.split()) + len(ai_reply.split())
    ChatSession.objects.filter(pk=session.pk).update(
        last_message_at=timezone.now(),
        total_tokens=session.total_tokens + word_count,
    )

    def _fmt(dt):
        return timezone.localtime(dt).strftime('%H:%M')

    return JsonResponse({
        'status': 'ok',
        'user_message': {
            'id':         user_msg.id,
            'role':       user_msg.role,
            'content':    user_msg.content,
            'created_at': _fmt(user_msg.created_at),
        },
        'ai_message': {
            'id':         ai_msg.id,
            'role':       ai_msg.role,
            'content':    ai_msg.content,
            'created_at': _fmt(ai_msg.created_at),
        },
    })


@login_required(login_url='/login/')
@require_POST
def delete_chat(request, session_id):
    """
    Soft-delete (archive) a ChatSession.
    Returns JSON with a redirect URL so the browser can navigate.
    """
    session        = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.status = 'archived'
    session.save(update_fields=['status', 'updated_at'])

    next_session = (
        ChatSession.objects
        .filter(user=request.user, status='active')
        .exclude(pk=session_id)
        .order_by('-last_message_at')
        .first()
    )
    redirect_url = f'/chat/{next_session.id}/' if next_session else '/chat/'

    return JsonResponse({'status': 'ok', 'redirect_url': redirect_url})


# ===========================================================================
# Memory System — Day 6
# ===========================================================================

@login_required(login_url='/login/')
def memory_list(request):
    """
    GET  — list all active memories, grouped by category.
    POST — add a new memory manually.
    """
    from .memory_service import CATEGORY_LABELS

    if request.method == 'POST':
        form = UserMemoryForm(request.POST)
        if form.is_valid():
            mem = form.save(commit=False)
            mem.user = request.user
            mem.is_active = True
            mem.save()
            messages.success(request, f'Memory "{mem.key}" saved successfully.')
            return redirect('assistant:memory_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserMemoryForm()

    all_memories = (
        UserMemory.objects
        .filter(user=request.user, is_active=True)
        .order_by('category', 'key')
    )

    # Group by category for template display
    grouped: dict[str, list] = {}
    for mem in all_memories:
        label = CATEGORY_LABELS.get(mem.category, mem.category.title())
        grouped.setdefault(label, []).append(mem)

    # Stats
    total          = all_memories.count()
    category_stats = []
    for cat_key, cat_label in CATEGORY_LABELS.items():
        cnt = all_memories.filter(category=cat_key).count()
        if cnt:
            category_stats.append({'label': cat_label, 'count': cnt})

    return render(request, 'assistant/memory.html', {
        'page_title':      'My Memories — Jarvis AI',
        'form':            form,
        'grouped':         grouped,
        'total':           total,
        'category_stats':  category_stats,
        'category_labels': CATEGORY_LABELS,
    })


@login_required(login_url='/login/')
def memory_edit(request, memory_id):
    """
    GET  — show edit form pre-filled with existing memory.
    POST — update the memory.
    """
    memory = get_object_or_404(UserMemory, id=memory_id, user=request.user)

    if request.method == 'POST':
        form = UserMemoryForm(request.POST, instance=memory)
        if form.is_valid():
            form.save()
            messages.success(request, f'Memory "{memory.key}" updated successfully.')
            return redirect('assistant:memory_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserMemoryForm(instance=memory)

    return render(request, 'assistant/memory_edit.html', {
        'page_title': f'Edit Memory — {memory.key} | Jarvis AI',
        'form':       form,
        'memory':     memory,
    })


@login_required(login_url='/login/')
@require_POST
def memory_delete(request, memory_id):
    """Soft-delete (deactivate) a memory, then redirect back to the list."""
    memory = get_object_or_404(UserMemory, id=memory_id, user=request.user)
    key = memory.key
    memory.is_active = False
    memory.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f'Memory "{key}" deleted.')
    return redirect('assistant:memory_list')


# ===========================================================================
# Knowledge Vault — Day 7
# ===========================================================================

@login_required(login_url='/login/')
def document_list(request):
    """
    GET  — list all uploaded documents.
    POST — upload a new document (extract text, store in DB).
    """
    from .forms import DocumentUploadForm
    from .models import UserDocument
    from .document_service import extract_text

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc                   = form.save(commit=False)
            doc.user              = request.user
            uploaded_file         = request.FILES['file']
            doc.original_filename = uploaded_file.name
            doc.file_size         = uploaded_file.size
            ext                   = uploaded_file.name.rsplit('.', 1)[-1].lower()
            doc.file_type         = ext

            # Auto-title from filename if not provided
            if not doc.title:
                doc.title = uploaded_file.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()

            doc.save()

            # Extract text in the same request (files are small)
            try:
                text = extract_text(doc.file.path, ext)
                doc.extracted_text = text
                doc.is_processed   = True
                doc.save(update_fields=['extracted_text', 'is_processed', 'updated_at'])
                messages.success(request, f'"{doc.title}" uploaded and processed successfully.')
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning('Text extraction failed: %s', exc)
                messages.warning(request, f'"{doc.title}" uploaded but text extraction failed.')

            return redirect('assistant:document_list')
        else:
            messages.error(request, 'Upload failed — please check the file and try again.')
    else:
        form = DocumentUploadForm()

    docs = UserDocument.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'assistant/documents.html', {
        'page_title': 'Knowledge Vault — Jarvis AI',
        'form':       form,
        'documents':  docs,
        'total':      docs.count(),
    })


@login_required(login_url='/login/')
@require_POST
def document_ask(request, doc_id):
    """
    AJAX endpoint: ask the AI a question about a specific document.
    Expects JSON body: {"question": "..."}
    Returns  JSON:    {"answer": "..."} or {"error": "..."}
    """
    from .models import UserDocument
    from .ai_service import generate_ai_response

    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)

    try:
        body     = json.loads(request.body)
        question = body.get('question', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request body.'}, status=400)

    if not question:
        return JsonResponse({'error': 'Question cannot be empty.'}, status=400)

    if not doc.extracted_text:
        return JsonResponse({
            'error': 'This document has no extracted text. '
                     'It may need to be re-uploaded or the format is not supported.'
        }, status=422)

    # Build a focused document context message
    doc_context = (
        f'[Document: "{doc.title}"]\n\n'
        f'{doc.extracted_text[:8000]}'  # keep well within token limits
    )

    history = [
        {'role': 'user',      'content': doc_context},
        {'role': 'assistant', 'content': 'I have read your document. What would you like to know?'},
    ]

    answer = generate_ai_response(
        user_message=question,
        history=history,
        user=request.user,
    )

    return JsonResponse({'answer': answer})


@login_required(login_url='/login/')
@require_POST
def document_delete(request, doc_id):
    """Delete an uploaded document (file + DB row)."""
    from .models import UserDocument
    import os

    doc = get_object_or_404(UserDocument, id=doc_id, user=request.user)
    title = doc.title

    # Delete the file from disk
    try:
        if doc.file and os.path.isfile(doc.file.path):
            os.remove(doc.file.path)
    except Exception:
        pass

    doc.delete()
    messages.success(request, f'"{title}" has been deleted.')
    return redirect('assistant:document_list')


# ===========================================================================
# Voice Settings — Day 7
# ===========================================================================

@login_required(login_url='/login/')
def voice_settings_view(request):
    """
    GET  — show voice settings form (create defaults if not exists).
    POST — save voice settings and sync to localStorage via template JS.
    """
    from .forms import VoiceSettingsForm
    from .models import VoiceSettings

    vs, _ = VoiceSettings.objects.get_or_create(
        user=request.user,
        defaults={
            'voice_gender': 'female',
            'language':     'en-IN',
            'auto_speak':   True,
            'speech_rate':  1.0,
            'speech_pitch': 1.1,
        },
    )

    if request.method == 'POST':
        form = VoiceSettingsForm(request.POST, instance=vs)
        if form.is_valid():
            form.save()
            messages.success(request, 'Voice settings saved!')
            return redirect('assistant:voice_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VoiceSettingsForm(instance=vs)

    return render(request, 'assistant/voice_settings.html', {
        'page_title': 'Voice Settings — Jarvis AI',
        'form':       form,
        'vs':         vs,
    })


# ===========================================================================
# Voice Assistant Page — Day 7 Enhancement
# ===========================================================================

@login_required(login_url='/login/')
def voice_assistant_view(request):
    """
    Dedicated voice assistant landing page.
    Finds or creates a persistent 'Voice Assistant' chat session for the user.
    """
    from .models import ChatSession, ChatMessage, UserDocument, VoiceSettings

    # Find or create a dedicated voice session (one per user)
    voice_session = ChatSession.objects.filter(
        user=request.user,
        title='Voice Assistant',
    ).first()

    if not voice_session:
        voice_session = ChatSession.objects.create(
            user=request.user,
            title='Voice Assistant',
        )

    # Last 30 messages, oldest first
    recent_messages = list(
        ChatMessage.objects.filter(session=voice_session)
        .order_by('-created_at')[:30]
    )
    recent_messages.reverse()

    # Processed documents for the document selector
    documents = UserDocument.objects.filter(
        user=request.user,
        is_processed=True,
    ).order_by('-created_at')

    # Voice settings (create defaults if missing)
    vs, _ = VoiceSettings.objects.get_or_create(
        user=request.user,
        defaults={
            'voice_gender': 'female',
            'language':     'en-IN',
            'auto_speak':   True,
            'speech_rate':  1.0,
            'speech_pitch': 1.1,
        },
    )

    user_name = request.user.first_name or request.user.username

    return render(request, 'assistant/voice_assistant.html', {
        'page_title':    'Voice Assistant — Jarvis AI',
        'voice_session': voice_session,
        'chat_messages': recent_messages,
        'documents':     documents,
        'vs':            vs,
        'user_name':     user_name,
    })


@login_required(login_url='/login/')
@require_POST
def voice_assistant_send(request):
    """
    AJAX endpoint for the voice assistant page.
    Accepts: { content, session_id, doc_id (optional) }
    Returns: { status, user_message, ai_message }
    """
    from .models import ChatSession, ChatMessage, UserDocument
    from .ai_service import generate_ai_response
    from .memory_service import extract_and_save_memories

    try:
        body       = json.loads(request.body)
        content    = body.get('content', '').strip()
        session_id = body.get('session_id')
        doc_id     = body.get('doc_id')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'status': 'error', 'message': 'Invalid request body.'}, status=400)

    if not content:
        return JsonResponse({'status': 'error', 'message': 'Message cannot be empty.'}, status=400)

    # Validate session ownership
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    # Build conversation history (last 20 messages)
    history = [
        {'role': m.role, 'content': m.content}
        for m in ChatMessage.objects.filter(session=session).order_by('-created_at')[:20]
    ]
    history.reverse()

    # Optionally prepend document context
    if doc_id:
        try:
            doc = UserDocument.objects.get(id=doc_id, user=request.user, is_processed=True)
            if doc.extracted_text:
                history = [
                    {
                        'role':    'user',
                        'content': f'[Document: "{doc.title}"]\n\n{doc.extracted_text[:6000]}',
                    },
                    {
                        'role':    'assistant',
                        'content': f'I\'ve read "{doc.title}". What would you like to know?',
                    },
                ] + history
        except UserDocument.DoesNotExist:
            pass

    # Save user message
    user_msg = ChatMessage.objects.create(
        session=session,
        role='user',
        content=content,
    )

    # Generate AI response
    ai_content = generate_ai_response(
        user_message=content,
        history=history,
        user=request.user,
    )

    # Save AI message
    ai_msg = ChatMessage.objects.create(
        session=session,
        role='assistant',
        content=ai_content,
    )

    # Background memory extraction (same as regular chat)
    # extract_and_save_memories signature: (user, user_message, session=None)
    try:
        extract_and_save_memories(
            user=request.user,
            user_message=content,
            session=session,
        )
    except Exception:
        pass

    return JsonResponse({
        'status': 'ok',
        'user_message': {
            'id':         user_msg.id,
            'content':    user_msg.content,
            'created_at': user_msg.created_at.strftime('%I:%M %p'),
        },
        'ai_message': {
            'id':         ai_msg.id,
            'content':    ai_msg.content,
            'created_at': ai_msg.created_at.strftime('%I:%M %p'),
        },
    })
