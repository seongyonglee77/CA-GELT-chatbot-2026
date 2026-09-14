/**
 * Deepgram Voice Agent classroom session store.
 *
 * This Web App only writes rows that the browser has already received from
 * Deepgram. It never performs speech recognition or calls a provider API.
 * Bind this project to a spreadsheet, or set the SPREADSHEET_ID script
 * property when using a standalone Apps Script project.
 */

var MODEL_ID = 'model_1_deepgram_agent';
var DEPLOYMENT_PATH = 'deepgram_voice_agent';
var PERSONA_VOICES = {
  deepgram_kit: 'flux-kit-en',
  deepgram_kai: 'flux-kai-en'
};
var DEGREE_LEVELS = {
  undergraduate: true,
  graduate: true
};
var ROLES = {
  user: true,
  assistant: true
};
var MAX = {
  clientTimestamp: 80,
  sessionId: 128,
  turnId: 128,
  studentId: 128,
  transcript: 4000
};
var HEADERS = [
  'server_timestamp',
  'client_timestamp',
  'session_id',
  'turn_id',
  'persona_id',
  'voice_id',
  'model_id',
  'deployment_path',
  'degree_level',
  'student_id',
  'role',
  'transcript'
];

function doGet() {
  var sessions = ensureSheet('Sessions');
  var transcript = ensureSheet('AgentTranscript');
  return jsonResponse({
    success: true,
    service: 'deepgram-voice-agent-store',
    status: 'ok',
    timestamp: new Date().toISOString(),
    sheets: {
      sessions: Math.max(0, sessions.getLastRow() - 1),
      agentTranscript: Math.max(0, transcript.getLastRow() - 1)
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
  if (data.type === 'session_start') return saveSessionStart(data);
  if (data.type === 'agent_turn') return saveAgentTurn(data);
  return jsonResponse({ success: false, error: 'Unsupported request type.' });
}

function saveSessionStart(data) {
  var validation = validateCommon(data, false);
  if (!validation.success) return jsonResponse(validation);

  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(5000);
    var sheet = ensureSheet('Sessions');
    sheet.appendRow(rowFor(data, '', '', validation.voiceId));
    return jsonResponse({ success: true, stored: true, sheet: 'Sessions' });
  } catch (_error) {
    return jsonResponse({ success: false, error: 'Session data could not be saved.' });
  } finally {
    try { lock.releaseLock(); } catch (_releaseError) {}
  }
}

function saveAgentTurn(data) {
  var validation = validateCommon(data, true);
  if (!validation.success) return jsonResponse(validation);

  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(5000);
    var sheet = ensureSheet('AgentTranscript');
    if (hasTurnRole(sheet, validation.turnId, validation.role)) {
      return jsonResponse({ success: true, stored: false, duplicate: true });
    }
    sheet.appendRow(rowFor(
      data,
      validation.turnId,
      validation.role,
      validation.voiceId,
      validation.transcript
    ));
    return jsonResponse({ success: true, stored: true, sheet: 'AgentTranscript' });
  } catch (_error) {
    return jsonResponse({ success: false, error: 'Transcript data could not be saved.' });
  } finally {
    try { lock.releaseLock(); } catch (_releaseError) {}
  }
}

function validateCommon(data, withTurn) {
  var personaId = boundedText(data.persona_id, 64);
  var voiceId = boundedText(data.voice_id, 64);
  var modelId = boundedText(data.model_id, 80);
  var deploymentPath = boundedText(data.deployment_path, 80);
  var degreeLevel = boundedText(data.degree_level, 32);
  var studentId = boundedText(data.student_id, MAX.studentId);
  var sessionId = boundedText(data.session_id, MAX.sessionId);
  var clientTimestamp = boundedText(data.client_timestamp, MAX.clientTimestamp);

  if (!personaId || !Object.prototype.hasOwnProperty.call(PERSONA_VOICES, personaId)) {
    return invalid('Invalid persona.');
  }
  if (voiceId !== PERSONA_VOICES[personaId]) return invalid('Invalid voice.');
  if (modelId !== MODEL_ID) return invalid('Invalid model.');
  if (deploymentPath !== DEPLOYMENT_PATH) return invalid('Invalid deployment.');
  if (!degreeLevel || !DEGREE_LEVELS[degreeLevel]) return invalid('Invalid degree level.');
  if (!studentId || !sessionId) return invalid('Student ID and session ID are required.');
  if (!clientTimestamp) return invalid('Client timestamp is required.');

  var result = {
    success: true,
    personaId: personaId,
    voiceId: voiceId,
    studentId: studentId,
    sessionId: sessionId,
    turnId: '',
    role: '',
    transcript: ''
  };
  if (withTurn) {
    result.turnId = boundedText(data.turn_id, MAX.turnId);
    result.role = boundedText(data.role, 16);
    result.transcript = boundedText(
      data.transcript !== undefined ? data.transcript : data.content,
      MAX.transcript
    );
    if (!result.turnId || !ROLES[result.role] || !result.transcript) {
      return invalid('Turn ID, role, and transcript are required.');
    }
  }
  return result;
}

function invalid(message) {
  return { success: false, error: message };
}

function boundedText(value, maxLength) {
  if (typeof value !== 'string') return '';
  var text = value.trim();
  if (!text || text.length > maxLength) return '';
  return text;
}

function rowFor(data, turnId, role, voiceId, transcript) {
  return [
    new Date().toISOString(),
    boundedText(data.client_timestamp, MAX.clientTimestamp),
    boundedText(data.session_id, MAX.sessionId),
    turnId,
    boundedText(data.persona_id, 64),
    voiceId,
    MODEL_ID,
    DEPLOYMENT_PATH,
    boundedText(data.degree_level, 32),
    boundedText(data.student_id, MAX.studentId),
    role,
    transcript || ''
  ];
}

function hasTurnRole(sheet, turnId, role) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return false;
  var values = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();
  for (var index = 0; index < values.length; index += 1) {
    if (String(values[index][3]) === turnId && String(values[index][10]) === role) {
      return true;
    }
  }
  return false;
}

function ensureSheet(name) {
  var spreadsheet = getSpreadsheet();
  var sheet = spreadsheet.getSheetByName(name);
  if (!sheet) sheet = spreadsheet.insertSheet(name);
  var headerRange = sheet.getRange(1, 1, 1, HEADERS.length);
  var current = headerRange.getValues()[0];
  var matches = HEADERS.every(function(header, index) {
    return String(current[index] || '') === header;
  });
  if (!matches) headerRange.setValues([HEADERS]);
  return sheet;
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
