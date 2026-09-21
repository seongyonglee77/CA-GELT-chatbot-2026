/**
 * Weekly classroom AI-persona register.
 *
 * Separate deployment from Code.gs. This script only maintains the weekly
 * persona table in the classroom spreadsheet; it does not create or store
 * conversation sessions or transcripts.
 *
 * Optional Script Properties:
 *   SPREADSHEET_ID      - target spreadsheet ID for a standalone script
 *   PERSONA_SHEET_NAME  - exact tab name; otherwise row-5 headers are detected
 *   CURRENT_WEEK        - fallback label, for example "3주차"
 *
 * The current classroom path is recorded as Model 1 unless this code and its
 * deployment are explicitly changed later.
 */

var DEFAULT_WEEK = '3주차';
var PERSONA_SHEET_NAME = '주차별 AI 페르소나';

var PERSONA_CATALOG = {
  deepgram_kit: {
    displayName: 'Kit',
    voiceId: 'flux-kit-en',
    provider: 'Deepgram Flux',
    nation: 'British',
    english: 'British English',
    personaType: 'fictionalized classroom persona',
    sourceGrounded: 'Deepgram-hosted Flux metadata; British masculine, young-adult voice; not a real-person identity.',
    fictionalized: 'Kit; 24; London; University College London; master’s student in Applied Linguistics.',
    role: 'One-to-one English conversation partner',
    topics: 'Language variation; ELF; multilingual classrooms; London life; cafés; study routines.',
    style: 'Concise, supportive, calm, meaning-first; brief useful corrections without interruption.',
    source: 'Deepgram Flux hosted voice catalog: flux-kit-en',
    rights: 'RIGHTS_PENDING',
    uses: 'Classroom Voice Agent; public/demo scope pending provider-terms confirmation.',
    profileFile: 'voices/personas/deepgram_kit.json',
    promptFile: 'prompts/voice_agents_system-prompt/deepgram_kit.md',
    settingsFile: 'prompts/raw_materials/deepgram_kit_code.json',
    evidence: 'history.md 2026-09-14; docs/1. GE-AI_technical-report.md §0.0.0'
  },
  deepgram_kai: {
    displayName: 'Kai',
    voiceId: 'flux-kai-en',
    provider: 'Deepgram Flux',
    nation: 'Singapore',
    english: 'Singaporean English',
    personaType: 'fictionalized classroom persona',
    sourceGrounded: 'Deepgram-hosted Flux metadata; Singaporean masculine, young-adult voice; not a real-person identity.',
    fictionalized: 'Kai; 23; Singapore; National University of Singapore; undergraduate business student.',
    role: 'One-to-one English conversation partner',
    topics: 'Business; social enterprise; local food; transport; neighbourhoods; practical planning.',
    style: 'Clear, calm, practical, encouraging, meaning-first; brief useful corrections without interruption.',
    source: 'Deepgram Flux hosted voice catalog: flux-kai-en',
    rights: 'RIGHTS_PENDING',
    uses: 'Classroom Voice Agent; public/demo scope pending provider-terms confirmation.',
    profileFile: 'voices/personas/deepgram_kai.json',
    promptFile: 'prompts/voice_agents_system-prompt/deepgram_kai.md',
    settingsFile: 'prompts/raw_materials/deepgram_kai_code.json',
    evidence: 'history.md 2026-09-14; docs/1. GE-AI_technical-report.md §0.0.0'
  },
  deepgram_hannah: {
    displayName: 'Hannah',
    voiceId: 'flux-hannah-en',
    provider: 'Deepgram Flux',
    nation: 'United States',
    english: 'American English (New York style)',
    personaType: 'fictionalized classroom persona',
    sourceGrounded: 'Deepgram-hosted Flux settings and provider voice metadata; not a real-person identity.',
    fictionalized: 'Hannah; 21; New York City; New York University Gallatin; undergraduate Fashion Design student; learning Korean.',
    role: 'One-to-one English conversation partner',
    topics: 'Fashion design; fashion history; The Metropolitan Museum of Art; SoHo and New York street style; Central Park; Korean language and K-culture; visual storytelling.',
    style: 'Warm, expressive, concise, visually minded; American English with a light New York flavor; meaning-first corrections.',
    source: 'Supplied Deepgram Agent settings: flux-hannah-en; provider-hosted voice metadata.',
    rights: 'RIGHTS_PENDING',
    uses: 'Classroom Voice Agent; public/demo scope pending provider-terms confirmation.',
    profileFile: 'voices/personas/deepgram_hannah.json',
    promptFile: 'prompts/voice_agents_system-prompt/deepgram_hannah.md',
    settingsFile: 'prompts/raw_materials/deepgram_Hannah_code.json',
    evidence: 'voices/personas/deepgram_hannah.json; prompts/voice_agents_system-prompt/deepgram_hannah.md; prompts/raw_materials/deepgram_Hannah_code.json'
  },
  deepgram_naveen: {
    displayName: 'Naveen',
    voiceId: 'flux-naveen-en',
    provider: 'Deepgram Flux',
    nation: 'India',
    english: 'Indian English',
    personaType: 'fictionalized classroom persona',
    sourceGrounded: 'Deepgram-hosted Flux settings and provider voice metadata; not a real-person identity.',
    fictionalized: 'Naveen; 23; New Delhi with Bengaluru roots; IIT Delhi; final-year undergraduate Computer Science and Engineering student; AI translation capstone.',
    role: 'One-to-one English conversation partner',
    topics: 'Python and software engineering; full-stack development; NLP; AI translation and language access; New Delhi and Bengaluru; K-culture; coding communities and student life.',
    style: 'Bright, friendly, energetic Indian English; plain technical explanations, light conversational warmth, and meaning-first corrections.',
    source: 'Supplied Deepgram Agent settings: flux-naveen-en; provider-hosted voice metadata.',
    rights: 'RIGHTS_PENDING',
    uses: 'Classroom Voice Agent; public/demo scope pending provider-terms confirmation.',
    profileFile: 'voices/personas/deepgram_naveen.json',
    promptFile: 'prompts/voice_agents_system-prompt/deepgram_naveen.md',
    settingsFile: 'prompts/raw_materials/deepgram_Naveen_code.json',
    evidence: 'voices/personas/deepgram_naveen.json; prompts/voice_agents_system-prompt/deepgram_naveen.md; prompts/raw_materials/deepgram_Naveen_code.json'
  }
};

var PERSONA_HEADERS = [
  '주차', '모델링방식', '소스', 'AI', 'Nation', 'English',
  'Voice ID', 'AI Provider', 'Agent 구성', 'Persona 유형',
  'Source-grounded 정보', 'Fictionalized 정보', 'Persona 역할',
  '대화 주제', '대화 스타일', '음성 출처', 'Identity clone 여부',
  'TTS Reference 사용 여부', 'TTS Fine-tuning 여부', '권리 상태',
  '사용 범위', 'Persona 파일', 'Prompt 파일', 'Settings 파일', '근거 기록'
];

function doGet(e) {
  var params = (e && e.parameter) || {};
  if (params.action === 'sync_personas') {
    return jsonResponse(syncPersonaCatalog(params.week || ''));
  }

  var personaSheet = ensurePersonaSheet();
  return jsonResponse({
    success: true,
    service: 'weekly-ai-persona-store',
    status: 'ok',
    timestamp: new Date().toISOString(),
    sheets: {
      weeklyPersonas: Math.max(0, personaSheet.getLastRow() - 5)
    }
  });
}

function doPost(e) {
  var data;
  try {
    var contents = e && e.postData && e.postData.contents;
    data = contents ? JSON.parse(contents) : ((e && e.parameter) || {});
  } catch (_error) {
    return jsonResponse({ success: false, error: 'Invalid JSON request.' });
  }

  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return jsonResponse({ success: false, error: 'Invalid request.' });
  }
  if (data.type === 'sync_personas') {
    return jsonResponse(syncPersonaCatalog(data.week || ''));
  }
  return jsonResponse({
    success: false,
    error: 'This endpoint only accepts type=sync_personas.'
  });
}

function syncPersonaCatalog(week) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(5000);
    var sheet = ensurePersonaSheet();
    var ids = Object.keys(PERSONA_CATALOG);
    var actions = [];
    for (var index = 0; index < ids.length; index += 1) {
      var result = upsertPersonaRow(sheet, ids[index], week, 'deepgram-voice');
      actions.push({ persona_id: ids[index], action: result.action });
    }
    return {
      success: true,
      sheet: sheet.getName(),
      week: weekLabel(week),
      actions: actions
    };
  } catch (_error) {
    return { success: false, error: 'Persona rows could not be synchronized.' };
  } finally {
    try { lock.releaseLock(); } catch (_releaseError) {}
  }
}

function upsertPersonaRow(sheet, personaId, requestedWeek, requestedSource) {
  var profile = PERSONA_CATALOG[personaId];
  if (!profile) throw new Error('Unknown persona.');

  var week = weekLabel(requestedWeek);
  var source = boundedText(requestedSource, 80) || 'deepgram-voice';
  var row = [
    week, 'Model 1', source, profile.displayName, profile.nation, profile.english,
    profile.voiceId, profile.provider, agentConfiguration(profile.voiceId),
    profile.personaType, profile.sourceGrounded, profile.fictionalized,
    profile.role, profile.topics, profile.style, profile.source,
    'No', 'No', 'No', profile.rights, profile.uses,
    profile.profileFile, profile.promptFile, profile.settingsFile, profile.evidence
  ];

  var lastRow = sheet.getLastRow();
  if (lastRow >= 6) {
    var existing = sheet.getRange(6, 1, lastRow - 5, PERSONA_HEADERS.length).getValues();
    for (var index = 0; index < existing.length; index += 1) {
      var current = existing[index];
      if (
        String(current[0]) === week &&
        String(current[1]) === 'Model 1' &&
        String(current[3]) === profile.displayName
      ) {
        // Preserve manually maintained A:F cells and refresh G:Y only.
        sheet.getRange(index + 6, 7, 1, PERSONA_HEADERS.length - 6)
          .setValues([row.slice(6)]);
        return { action: 'updated', sheet: sheet.getName() };
      }
    }
  }

  sheet.getRange(Math.max(6, sheet.getLastRow() + 1), 1, 1, row.length)
    .setValues([row]);
  return { action: 'inserted', sheet: sheet.getName() };
}

function ensurePersonaSheet() {
  var spreadsheet = getSpreadsheet();
  var properties = PropertiesService.getScriptProperties();
  var configuredName = properties.getProperty('PERSONA_SHEET_NAME');
  var sheet = null;

  if (configuredName) sheet = spreadsheet.getSheetByName(configuredName);
  if (!sheet) sheet = spreadsheet.getSheetByName(PERSONA_SHEET_NAME);
  if (!sheet) sheet = findPersonaHeaderSheet(spreadsheet);
  if (!sheet) sheet = spreadsheet.insertSheet(configuredName || PERSONA_SHEET_NAME);

  var baseHeaders = PERSONA_HEADERS.slice(0, 6);
  var baseRange = sheet.getRange(5, 1, 1, baseHeaders.length);
  var baseCurrent = baseRange.getValues()[0];
  var baseChanged = false;
  for (var index = 0; index < baseHeaders.length; index += 1) {
    if (!String(baseCurrent[index] || '').trim()) {
      baseCurrent[index] = baseHeaders[index];
      baseChanged = true;
    }
  }
  if (baseChanged) baseRange.setValues([baseCurrent]);

  // Replace placeholder headers such as "여기부터 채워" and "..." in G:Y.
  sheet.getRange(5, 7, 1, PERSONA_HEADERS.length - 6)
    .setValues([PERSONA_HEADERS.slice(6)]);
  return sheet;
}

function findPersonaHeaderSheet(spreadsheet) {
  var sheets = spreadsheet.getSheets();
  var expected = PERSONA_HEADERS.slice(0, 6);
  for (var sheetIndex = 0; sheetIndex < sheets.length; sheetIndex += 1) {
    var sheet = sheets[sheetIndex];
    if (sheet.getLastRow() < 5 || sheet.getLastColumn() < 6) continue;
    var values = sheet.getRange(5, 1, 1, 6).getValues()[0];
    var matches = expected.every(function(header, index) {
      return String(values[index] || '').trim() === header;
    });
    if (matches) return sheet;
  }
  return null;
}

function agentConfiguration(voiceId) {
  return 'Listen: flux-general-en; Think: gemini-3.1-flash-lite; Speak: ' + voiceId;
}

function weekLabel(value) {
  var requested = boundedText(value, 32);
  if (requested) return requested;
  var configured = PropertiesService.getScriptProperties().getProperty('CURRENT_WEEK');
  return boundedText(configured, 32) || DEFAULT_WEEK;
}

function boundedText(value, maxLength) {
  if (typeof value !== 'string') return '';
  var text = value.trim();
  if (!text || text.length > maxLength) return '';
  return text;
}

function getSpreadsheet() {
  var propertyId = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (propertyId) return SpreadsheetApp.openById(propertyId);
  var active = SpreadsheetApp.getActiveSpreadsheet();
  if (active) return active;
  throw new Error('Spreadsheet is not configured.');
}

function jsonResponse(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
