"""
Forms for the assistant app — Day 7: Document + Voice Settings forms added.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import UserMemory, UserDocument, VoiceSettings


# ---------------------------------------------------------------------------
# Registration Form
# ---------------------------------------------------------------------------
class RegisterForm(UserCreationForm):
    """
    Extended registration form that adds an email field to Django's
    built-in UserCreationForm. All fields include Bootstrap-compatible
    widgets and helpful placeholder text.
    """

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control jarvis-input',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
            'id': 'id_email',
        }),
        help_text='We\'ll never share your email with anyone.',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ---- username ----
        self.fields['username'].widget.attrs.update({
            'class': 'form-control jarvis-input',
            'placeholder': 'Choose a username',
            'autocomplete': 'username',
            'id': 'id_username',
        })
        self.fields['username'].help_text = (
            'Letters, digits, and @/./+/-/_ only. Max 150 characters.'
        )

        # ---- password1 ----
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control jarvis-input',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password',
            'id': 'id_password1',
        })
        self.fields['password1'].help_text = (
            'At least 8 characters. Cannot be entirely numeric.'
        )

        # ---- password2 ----
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control jarvis-input',
            'placeholder': 'Repeat your password',
            'autocomplete': 'new-password',
            'id': 'id_password2',
        })
        self.fields['password2'].help_text = 'Enter the same password as above.'

    def clean_email(self):
        """Ensure the email address is unique across all users."""
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. Try logging in.'
            )
        return email

    def save(self, commit=True):
        """Save the user with the normalised email."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user


# ---------------------------------------------------------------------------
# Login Form
# ---------------------------------------------------------------------------
class LoginForm(AuthenticationForm):
    """
    Custom login form extending Django's AuthenticationForm.
    Adds Bootstrap-compatible widgets and a 'Remember Me' checkbox.
    """

    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_remember_me',
        }),
        label='Remember me for 30 days',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ---- username ----
        self.fields['username'].widget.attrs.update({
            'class': 'form-control jarvis-input',
            'placeholder': 'Your username',
            'autocomplete': 'username',
            'id': 'id_login_username',
            'autofocus': True,
        })

        # ---- password ----
        self.fields['password'].widget.attrs.update({
            'class': 'form-control jarvis-input',
            'placeholder': 'Your password',
            'autocomplete': 'current-password',
            'id': 'id_login_password',
        })


# ---------------------------------------------------------------------------
# UserMemory Form — Day 6: Memory Management
# ---------------------------------------------------------------------------
class UserMemoryForm(forms.ModelForm):
    """Form for manually adding or editing a UserMemory entry."""

    class Meta:
        model  = UserMemory
        fields = ('key', 'value', 'category')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['key'].widget.attrs.update({
            'class':       'form-control jarvis-input',
            'placeholder': 'e.g. name, favorite_language, career_goal',
            'id':          'id_mem_key',
        })
        self.fields['key'].help_text = (
            'Lowercase, use underscores. E.g. "favorite_language"'
        )

        self.fields['value'].widget = forms.Textarea(attrs={
            'class':       'form-control jarvis-input',
            'placeholder': 'The value to remember…',
            'rows':        3,
            'id':          'id_mem_value',
        })

        self.fields['category'].widget.attrs.update({
            'class': 'form-select jarvis-input',
            'id':    'id_mem_category',
        })

    def clean_key(self):
        """Normalise key to lowercase snake_case."""
        key = self.cleaned_data.get('key', '').strip().lower()
        key = key.replace(' ', '_').replace('-', '_')
        return key


# ---------------------------------------------------------------------------
# DocumentUploadForm — Day 7: Knowledge Vault
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'txt'}
MAX_FILE_SIZE_MB   = 10


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading a document to the Knowledge Vault."""

    class Meta:
        model  = UserDocument
        fields = ('title', 'file')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['title'].required = False
        self.fields['title'].widget.attrs.update({
            'class':       'form-control jarvis-input',
            'placeholder': 'Document title (optional — auto-detected from filename)',
            'id':          'id_doc_title',
        })

        self.fields['file'].widget.attrs.update({
            'class':  'form-control jarvis-input',
            'id':     'id_doc_file',
            'accept': '.pdf,.docx,.pptx,.txt',
        })
        self.fields['file'].help_text = (
            f'Allowed: PDF, DOCX, PPTX, TXT — max {MAX_FILE_SIZE_MB} MB.'
        )

    def clean_file(self):
        f   = self.cleaned_data.get('file')
        if not f:
            raise forms.ValidationError('Please choose a file to upload.')

        ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else ''
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                f'Unsupported file type ".{ext}". Allowed: PDF, DOCX, PPTX, TXT.'
            )

        if f.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(
                f'File is too large ({f.size / (1024*1024):.1f} MB). Max is {MAX_FILE_SIZE_MB} MB.'
            )
        return f


# ---------------------------------------------------------------------------
# VoiceSettingsForm — Day 7: Voice Preferences
# ---------------------------------------------------------------------------
class VoiceSettingsForm(forms.ModelForm):
    """Form for editing the user's voice assistant preferences."""

    class Meta:
        model  = VoiceSettings
        fields = ('voice_gender', 'language', 'auto_speak', 'speech_rate', 'speech_pitch')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['voice_gender'].widget.attrs.update({
            'class': 'form-select jarvis-input',
            'id':    'voiceGenderSelect',
        })

        self.fields['language'].widget.attrs.update({
            'class': 'form-select jarvis-input',
            'id':    'voiceLangSelect',
        })

        self.fields['auto_speak'].widget = forms.CheckboxInput(attrs={
            'class': 'form-check-input js-auto-speak-toggle',
            'id':    'autoSpeakToggle',
            'role':  'switch',
        })
        self.fields['auto_speak'].label = 'Auto-speak AI responses'

        self.fields['speech_rate'].widget = forms.NumberInput(attrs={
            'class': 'form-range',
            'type':  'range',
            'min':   '0.5',
            'max':   '2.0',
            'step':  '0.1',
            'id':    'voiceRateSlider',
        })
        self.fields['speech_rate'].label      = 'Speaking speed'
        self.fields['speech_rate'].help_text  = '0.5 (slow) → 1.0 (normal) → 2.0 (fast)'

        self.fields['speech_pitch'].widget = forms.NumberInput(attrs={
            'class': 'form-range',
            'type':  'range',
            'min':   '0.0',
            'max':   '2.0',
            'step':  '0.1',
            'id':    'voicePitchSlider',
        })
        self.fields['speech_pitch'].label     = 'Voice pitch'
        self.fields['speech_pitch'].help_text = '0.0 (low) → 1.0 (normal) → 2.0 (high)'
