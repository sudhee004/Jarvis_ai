/**
 * voice.js — Jarvis Advanced Voice Assistant (Day 7)
 *
 * Features:
 *   - Speech-to-Text  : Web Speech API  (en-IN / kn-IN / mixed Kannada-English)
 *   - Text-to-Speech  : SpeechSynthesis  (auto-selects best female voice)
 *   - Voice Commands  : navigation + control phrases
 *   - Auto-speak toggle
 *   - Keyboard shortcut: Ctrl+M to toggle mic
 *   - Config persisted in localStorage
 *
 * Public API (window.JarvisVoice):
 *   .startListening()   — begin STT
 *   .stopListening()    — end STT
 *   .speak(text)        — TTS
 *   .stopSpeaking()     — cancel TTS
 *   .readLastResponse() — speak the most recent AI bubble
 *   .onAIResponse(text) — call from chat.js after AI reply arrives
 *   .saveConfig(obj)    — update one or more config keys
 *   .getConfig()        — return current config object
 */

'use strict';

/* ============================================================
   Voice Command Registry
   pattern: RegExp matched against transcript (case-insensitive)
   action : zero-arg function to execute
============================================================ */
const VOICE_COMMANDS = [
  { pattern: /\b(open|go to|navigate to)\s+dashboard\b/i, action: () => location.href = '/dashboard/' },
  { pattern: /\b(open|go to)\s+memory\b/i,               action: () => location.href = '/memory/' },
  { pattern: /\b(open|go to)\s+chat\b/i,                 action: () => location.href = '/chat/' },
  { pattern: /\b(open|go to)\s+documents?\b/i,           action: () => location.href = '/documents/' },
  { pattern: /\b(open|go to)\s+settings?\b/i,            action: () => location.href = '/settings/voice/' },
  { pattern: /\bstop speak(ing)?\b/i,                    action: () => window.JarvisVoice?.stopSpeaking() },
  { pattern: /\bstart listen(ing)?\b/i,                  action: () => window.JarvisVoice?.startListening() },
  { pattern: /\bstop listen(ing)?\b/i,                   action: () => window.JarvisVoice?.stopListening() },
  { pattern: /\bread (last |the )?response\b/i,          action: () => window.JarvisVoice?.readLastResponse() },
  { pattern: /\bnew chat\b/i,                            action: () => document.getElementById('newChatBtn')?.click() },
];

/* ============================================================
   Default config
============================================================ */
const DEFAULT_CONFIG = {
  autoSpeak:     true,
  rate:          1.0,
  pitch:         1.1,
  volume:        1.0,
  lang:          'en-IN',   // en-IN handles mixed Kannada-English well
  gender:        'female',
};

/* ============================================================
   JarvisVoice — Main Voice Engine
============================================================ */
class JarvisVoice {
  constructor() {
    this.synth        = window.speechSynthesis;
    this.recognition  = null;
    this.voices       = [];
    this.selectedVoice = null;
    this.isListening  = false;
    this.isSpeaking   = false;

    this._config = this._loadConfig();
    this._pendingUtterance = null;

    this._initSynthesis();
    this._initRecognition();
    this._bindUI();
    this._updateUI();

    console.log('[Jarvis Voice] Ready. Config:', this._config);
  }

  /* ----------------------------------------------------------
     Config
  ---------------------------------------------------------- */
  _loadConfig() {
    try {
      const stored = JSON.parse(localStorage.getItem('jarvisVoiceCfg') || '{}');
      return { ...DEFAULT_CONFIG, ...stored };
    } catch { return { ...DEFAULT_CONFIG }; }
  }

  saveConfig(updates) {
    Object.assign(this._config, updates);
    try { localStorage.setItem('jarvisVoiceCfg', JSON.stringify(this._config)); }
    catch { /* storage unavailable */ }
    // Re-apply to recognition if lang changed
    if (this.recognition && updates.lang) {
      this.recognition.lang = updates.lang === 'mixed' ? 'en-IN' : updates.lang;
    }
    // Re-select voice if gender changed
    if (updates.gender) this.selectedVoice = this._selectVoice();
    this._updateUI();
  }

  getConfig() { return { ...this._config }; }

  /* ----------------------------------------------------------
     Speech Synthesis (TTS)
  ---------------------------------------------------------- */
  _initSynthesis() {
    if (!('speechSynthesis' in window)) {
      console.warn('[Jarvis Voice] TTS not supported in this browser.');
      return;
    }
    const load = () => {
      this.voices       = this.synth.getVoices();
      this.selectedVoice = this._selectVoice();
      console.log('[Jarvis Voice] TTS voice:', this.selectedVoice?.name ?? 'default');
    };
    load();
    this.synth.onvoiceschanged = load;
  }

  _selectVoice() {
    if (!this.voices.length) return null;

    if (this._config.gender === 'male') {
      // Male preference order
      const malePriority = [
        v => v.name.includes('David'),
        v => v.name.includes('James'),
        v => v.name.includes('Male'),
        v => v.name.includes('Ravi'),
        v => v.lang === 'en-IN' && !this._isFemaleVoice(v),
        v => v.lang.startsWith('en'),
      ];
      for (const test of malePriority) {
        const m = this.voices.find(test);
        if (m) return m;
      }
      return this.voices.find(v => v.lang.startsWith('en')) ?? this.voices[0];
    }

    // Female preference order (priority 1 → highest)
    const femalePriority = [
      v => v.name === 'Google UK English Female',
      v => v.name.includes('Heera'),                    // Microsoft en-IN female
      v => v.name === 'Microsoft Aria Online (Natural) - English (United States)',
      v => v.name.includes('Zira'),
      v => v.name.includes('Samantha'),
      v => v.name.includes('Karen'),
      v => v.name.includes('Victoria'),
      v => v.name.toLowerCase().includes('female'),
      v => v.lang === 'en-IN',
      v => v.lang === 'en-GB',
      v => v.lang.startsWith('en'),
    ];
    for (const test of femalePriority) {
      const m = this.voices.find(test);
      if (m) return m;
    }
    return this.voices[0];
  }

  _isFemaleVoice(v) {
    const name = v.name.toLowerCase();
    return name.includes('female') || name.includes('zira') ||
           name.includes('heera') || name.includes('samantha') ||
           name.includes('karen') || name.includes('victoria');
  }

  speak(text, onEnd = null) {
    if (!('speechSynthesis' in window)) { onEnd?.(); return; }
    if (!this._config.autoSpeak && !this._forceSpeak) { onEnd?.(); return; }

    this.stopSpeaking();

    // Strip markdown for cleaner TTS
    const clean = text
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/\*(.+?)\*/g,     '$1')
      .replace(/`(.+?)`/g,       '$1')
      .replace(/#{1,6}\s*/g,     '')
      .replace(/•\s*/g,          '')
      .replace(/\n{2,}/g,        '. ')
      .replace(/\n/g,            ' ')
      .replace(/\s{2,}/g,        ' ')
      .trim();

    if (!clean) { onEnd?.(); return; }

    const utt    = new SpeechSynthesisUtterance(clean);
    utt.voice    = this.selectedVoice ?? this._selectVoice();
    utt.rate     = this._config.rate;
    utt.pitch    = this._config.pitch;
    utt.volume   = this._config.volume;
    utt.lang     = utt.voice?.lang ?? this._config.lang;

    utt.onstart  = () => { this.isSpeaking = true;  this._updateUI(); };
    utt.onend    = () => { this.isSpeaking = false; this._updateUI(); onEnd?.(); };
    utt.onerror  = () => { this.isSpeaking = false; this._updateUI(); };

    this._pendingUtterance = utt;
    this.synth.speak(utt);
    this.isSpeaking = true;
    this._updateUI();
  }

  /** Force-speak regardless of autoSpeak toggle (called by per-message speak button). */
  speakForce(text) {
    this._forceSpeak = true;
    this.speak(text, () => { this._forceSpeak = false; });
  }

  stopSpeaking() {
    if (this.synth.speaking || this.synth.pending) this.synth.cancel();
    this.isSpeaking = false;
    this._updateUI();
  }

  readLastResponse() {
    const bubbles = document.querySelectorAll('.ai-bubble');
    if (bubbles.length) this.speakForce(bubbles[bubbles.length - 1].innerText);
  }

  /* ----------------------------------------------------------
     Speech Recognition (STT)
  ---------------------------------------------------------- */
  _initRecognition() {
    const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SR) {
      console.warn('[Jarvis Voice] STT not supported. Use Chrome or Edge.');
      return;
    }

    const r               = new SR();
    r.continuous          = false;
    r.interimResults      = true;
    r.maxAlternatives     = 3;
    r.lang                = this._config.lang === 'mixed' ? 'en-IN' : this._config.lang;

    r.onstart = () => { this.isListening = true;  this._updateUI(); };
    r.onend   = () => { this.isListening = false; this._updateUI(); };

    r.onresult = (event) => {
      let interim = '', final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t;
        else interim += t;
      }

      const inp = document.getElementById('messageInput');
      if (inp) inp.value = final || interim;

      if (final.trim()) this._handleTranscript(final.trim());
    };

    r.onerror = (e) => {
      this.isListening = false;
      this._updateUI();
      if (e.error === 'not-allowed') {
        this._showError('Microphone permission denied. Please allow it in your browser settings.');
      } else if (e.error !== 'no-speech') {
        console.warn('[Jarvis Voice] STT error:', e.error);
      }
    };

    this.recognition = r;
  }

  startListening() {
    if (!this.recognition) {
      this._showError('Voice input not supported in this browser. Please use Chrome or Edge.');
      return;
    }
    if (this.isListening) return;
    if (this.isSpeaking) this.stopSpeaking();

    this.recognition.lang = this._config.lang === 'mixed' ? 'en-IN' : this._config.lang;

    try { this.recognition.start(); }
    catch (e) { console.error('[Jarvis Voice] Could not start recognition:', e); }
  }

  stopListening() {
    if (this.recognition && this.isListening) this.recognition.stop();
  }

  _handleTranscript(text) {
    // Check voice commands first
    for (const cmd of VOICE_COMMANDS) {
      if (cmd.pattern.test(text)) { cmd.action(); return; }
    }

    // Allow specialized pages (e.g. Voice Assistant) to override default behaviour.
    // Set  window.onJarvisTranscript = (text) => { ... }  before voice.js initialises.
    if (typeof window.onJarvisTranscript === 'function') {
      window.onJarvisTranscript(text);
      return;
    }

    // Default: fill the chat input and submit the chat form
    const inp  = document.getElementById('messageInput');
    const form = document.getElementById('messageForm');
    if (inp && form) {
      inp.value = text;
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      setTimeout(() => form.requestSubmit(), 350);
    }
  }

  /* ----------------------------------------------------------
     UI binding
  ---------------------------------------------------------- */
  _bindUI() {
    // Mic toggle button
    document.addEventListener('click', (e) => {
      if (e.target.closest('#micBtn')) {
        if (this.isListening) this.stopListening();
        else this.startListening();
      }
    });

    // Stop-speak button
    document.addEventListener('click', (e) => {
      if (e.target.closest('#stopSpeakBtn')) this.stopSpeaking();
    });

    // Auto-speak toggle (settings + chat header)
    document.querySelectorAll('.js-auto-speak-toggle').forEach(el => {
      el.checked = this._config.autoSpeak;
      el.addEventListener('change', (e) => {
        this.saveConfig({ autoSpeak: e.target.checked });
        document.querySelectorAll('.js-auto-speak-toggle').forEach(t => t.checked = e.target.checked);
        if (!e.target.checked) this.stopSpeaking();
      });
    });

    // Per-message speak buttons (event delegation)
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.msg-speak-btn');
      if (!btn) return;
      this.speakForce(btn.dataset.text || '');
    });

    // Keyboard shortcut: Ctrl+M
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'm') {
        e.preventDefault();
        if (this.isListening) this.stopListening();
        else this.startListening();
      }
    });

    // Voice settings sliders (live preview)
    const rateSlider  = document.getElementById('voiceRateSlider');
    const pitchSlider = document.getElementById('voicePitchSlider');
    if (rateSlider)  rateSlider.addEventListener('input',  () => this.saveConfig({ rate:  parseFloat(rateSlider.value) }));
    if (pitchSlider) pitchSlider.addEventListener('input', () => this.saveConfig({ pitch: parseFloat(pitchSlider.value) }));

    // Test voice button
    const testBtn = document.getElementById('testVoiceBtn');
    if (testBtn) {
      testBtn.addEventListener('click', () => {
        this.speakForce("Hello! I am Jarvis, your personal AI assistant. How can I help you today?");
      });
    }

    // Lang selector
    const langSel = document.getElementById('voiceLangSelect');
    if (langSel) {
      langSel.value = this._config.lang;
      langSel.addEventListener('change', () => this.saveConfig({ lang: langSel.value }));
    }

    // Gender selector
    const genderSel = document.getElementById('voiceGenderSelect');
    if (genderSel) {
      genderSel.value = this._config.gender;
      genderSel.addEventListener('change', () => this.saveConfig({ gender: genderSel.value }));
    }
  }

  _updateUI() {
    // Mic button
    const mic = document.getElementById('micBtn');
    if (mic) {
      mic.classList.toggle('listening', this.isListening);
      mic.setAttribute('aria-pressed', String(this.isListening));
      mic.title = this.isListening ? 'Stop listening (Ctrl+M)' : 'Start voice input (Ctrl+M)';
      const icon = mic.querySelector('i');
      if (icon) {
        icon.className = this.isListening ? 'bi bi-stop-circle-fill' : 'bi bi-mic-fill';
      }
    }

    // Status bar
    const listenEl = document.querySelector('.status-listening');
    const speakEl  = document.querySelector('.status-speaking');
    if (listenEl) listenEl.classList.toggle('active', this.isListening);
    if (speakEl)  speakEl.classList.toggle('active', this.isSpeaking);

    // Stop-speak button
    const stopBtn = document.getElementById('stopSpeakBtn');
    if (stopBtn) stopBtn.style.display = this.isSpeaking ? 'inline-flex' : 'none';

    // Auto-speak indicator in header
    const speakingBadge = document.getElementById('speakingBadge');
    if (speakingBadge) speakingBadge.style.display = this.isSpeaking ? 'inline-flex' : 'none';
  }

  /* ----------------------------------------------------------
     Hook: called by chat.js after each AI response
  ---------------------------------------------------------- */
  onAIResponse(text) {
    if (this._config.autoSpeak) this.speak(text);
  }

  /* ----------------------------------------------------------
     Helpers
  ---------------------------------------------------------- */
  _showError(msg) {
    const bar = document.getElementById('voiceErrorBar');
    if (bar) {
      bar.textContent = msg;
      bar.style.display = 'block';
      setTimeout(() => { bar.style.display = 'none'; }, 5000);
    } else {
      console.warn('[Jarvis Voice]', msg);
    }
  }
}

/* ============================================================
   Bootstrap
============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  window.JarvisVoice = new JarvisVoice();
});
