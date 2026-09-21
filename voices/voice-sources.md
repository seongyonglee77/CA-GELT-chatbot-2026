# Voice Sources

음성 AI에 실제로 사용하거나 사용을 검토하는 음성·전사·권리 정보를 한 곳에서 관리하는 운영 문서다.

이 문서는 음성 파일 자체를 대체하지 않는다. 원본과 파생 파일은 `voices/` 아래에 보관하고, 이 문서에는 source ID·파일 경로·처리 상태·허가 범위·사용 목적·근거를 기록한다.

## 1. 사용 원칙

- 공개 코퍼스의 음성을 실제 개인의 identity clone으로 표시하지 않는다.
- 홈페이지에는 개인 이름 대신 승인된 `persona_id`와 voice/persona label만 표시한다.
- 음성 사용은 다음 권한을 분리해 확인한다.
  - research analysis
  - STT/transcription
  - TTS reference audio
  - chatbot output
  - public website/demo
  - TTS fine-tuning
  - LLM/text fine-tuning
- 권리가 확인되지 않은 음성은 내부 QC·alignment·STT 검증에만 사용하고, TTS reference나 공개 출력에는 사용하지 않는다.
- 원본 음성은 수정하지 않는다. 파생 파일은 processing log와 source file을 함께 기록한다.
- TTS reference clip은 승인된 clean audio에서 20–60초를 추출하고, matching transcript를 함께 보관한다.

## 2. 상태값

| 상태 | 의미 |
|---|---|
| `CANDIDATE` | 후보로 조사 중이며 실제 사용하지 않음 |
| `ACQUIRED` | 파일을 확보했으나 권리·품질 확인이 남음 |
| `QC_READY` | 기술적 정제와 기본 QC 완료 |
| `RIGHTS_PENDING` | source는 있으나 TTS/chatbot/public 사용 허가 미확인 |
| `APPROVED_INTERNAL` | 내부 연구·pipeline 검증 승인 |
| `APPROVED_TTS` | TTS reference 또는 TTS 학습 사용 승인 |
| `APPROVED_PUBLIC` | 홈페이지·외부 demo 출력 승인 |
| `REJECTED` | 사용하지 않음 |

## 3. 현재 Model 1 baseline

| 항목 | 값 |
|---|---|
| `model_id` | `model1` |
| `persona_id` | `icnale_chn_004_student` |
| `voice_id` | `icnale_chn_004_student_voice` |
| 표시 label | `Voice Persona CHN-004` (임시) |
| source | ICNALE Spoken Dialogue, `ICNALE_SD_CHN_004` |
| source role | Student, `SPEAKER_01` |
| 현재 상태 | `QC_READY` + `APPROVED_PUBLIC` (사용자 승인 보고; research/TTS/chatbot/public/LLM-text/cloud scope 포함) |
| 사용 목적 | Model 1 첫 pipeline baseline 후보 |
| 원본/clean base | `voices/Asian_Learners_ICNALE/Spoken_dialogue/model1_pilot/04_student_audio_pending/ICNALE_SD_CHN_004/ICNALE_SD_CHN_004_STUDENT_CLEAN.wav` |
| clean base 설명 | 인터뷰어 구간과 32:30–38:27 일본어 구간을 제외한 student-only clean audio, 약 19분 |
| reference clip | clean base에서 20–60초를 별도 추출 예정 |
| matching transcript | `voices/Asian_Learners_ICNALE/Spoken_dialogue/model1_pilot/03_qc/ICNALE_SD_CHN_004_transcript.csv`에서 clip 구간에 맞게 추출 예정 |
| 권리 조건 | 사용자가 research, TTS, chatbot output, public demo, LLM text training, third-party cloud processing 전체 허가를 확인함. 승인 이메일은 project owner가 보관하고 repository에는 복사하지 않는다. |

### 3.1 CHN_004 파생 파일 역할

| 파일 | 역할 | 사용 판정 |
|---|---|---|
| `ICNALE_SD_CHN_004_STUDENT_CLEAN.wav` | 최종 student-only clean base | reference clip 추출 원본 |
| `ICNALE_SD_CHN_004_SPEAKER_01_CLEAN_TIMELINE.wav` | 원본 시간축 보존본 | QC·transcript alignment용 |
| `ICNALE_SD_CHN_004_STUDENT_PROVISIONAL.wav` | 이전 provisional masking 결과 | 사용하지 않음 |
| `ICNALE_SD_CHN_004_SPEAKER_01_CONCATENATED.wav` | 최종 제외 전 concatenated 후보 | canonical reference로 사용하지 않음 |
| `ICNALE_SD_CHN_004_student_audio_exclusions.csv` | 제외 구간 audit log | 반드시 보존 |
| `ICNALE_SD_CHN_004_export_summary.csv` | 화자별 export 요약 | 처리 근거 |

## 4. 현재 확보했거나 조사 중인 음성 source

| `source_id` | 위치/자료 | 성격 | 예상 사용 | 상태 | 남은 확인 |
|---|---|---|---|---|---|
| `ICNALE_SD_CHN_004` | `voices/Asian_Learners_ICNALE/Spoken_dialogue/` | learner interview dialogue | Model 1 baseline, Model 3 dialogue/reference 후보 | `APPROVED_PUBLIC` | 승인 이메일은 project owner 보관; 전체 permitted-use scope 확인 |
| `ICNALE_SD_IDN_001` | `voices/Asian_Learners_ICNALE/Spoken_dialogue/` | learner interview dialogue | 후속 voice/persona 후보 | `ACQUIRED` | role mapping, student-only export, rights |
| `ICNALE_SD_JPN_002` | `voices/Asian_Learners_ICNALE/Spoken_dialogue/` | learner interview dialogue | 후속 voice/persona 후보 | `ACQUIRED` | role mapping, student-only export, rights |
| `SLR45_USA` | `voices/Reading_SLR/SLR45 USA/` | controlled/read speech | voice-class acoustic/reference 후보 | `CANDIDATE` | license, TTS/public use, speaker metadata |
| `SLR70_Nigeria_male` | `voices/Reading_SLR/SLR70_Nigeria_male/` | Nigerian English read speech | voice-class/reference 후보 | `CANDIDATE` | license, TTS/public use, speaker metadata |
| `SLR70_Nigeria_female` | `voices/Reading_SLR/SLR70_Nigeria_female/` | Nigerian English read speech | voice-class/reference 후보 | `CANDIDATE` | license, TTS/public use, speaker metadata |
| `SLR83_UK` | `voices/Reading_SLR/UK/` | UK read speech | voice-class/reference 후보 | `CANDIDATE` | exact corpus/license and TTS use |
| `SLR762_Mandarin` | `voices/Reading_SLR/SLR762_Mandarin/` | Mandarin L1 learner speech | voice-class/reference 후보 | `CANDIDATE` | license, TTS/public use, speaker metadata |
| `SG_NCS_SPEAKER2006` | `voices/Singapore/SPEAKER2006/` | controlled read speech with spoken-like register variation | pronunciation, prosody, acoustic comparison | `ACQUIRED` | source license, consent, permitted TTS scope |
| `SG_NCS_SPEAKER2001` | `voices/Singapore/SPEAKER2001/` | controlled read speech with spoken-like register variation | pronunciation, prosody, acoustic comparison | `ACQUIRED` | source license, consent, permitted TTS scope |
| `SG_NCS_SPEAKER0001` | `voices/Singapore/SPEAKER0001/` | controlled read speech with spoken-like register variation | pronunciation, prosody, acoustic comparison | `ACQUIRED` | source license, consent, permitted TTS scope |
| `2023_TQ_Australian` | `voices/2023_TQ/Australian student.m4a` | prior student recording | future candidate only | `CANDIDATE` | consent, speaker metadata, use scope |
| `2023_TQ_Thai` | `voices/2023_TQ/Thai student.m4a` | prior student recording | future candidate only | `CANDIDATE` | consent, speaker metadata, use scope |
| `2023_TQ_Philippines` | `voices/2023_TQ/Philippines students.m4a` | prior student recording | future candidate only | `CANDIDATE` | consent, speaker metadata, use scope |

### 4.1 Deepgram Flux hosted classroom voices

These are provider-hosted TTS voices, not downloaded recordings and not
identity clones. The persona biographies are fictionalized for classroom use;
the voice catalog characteristics are the only source-grounded voice facts.

| `source_id` | 위치/자료 | 성격 | 예상 사용 | 상태 | 남은 확인 |
|---|---|---|---|---|---|
| `DEEPGRAM_FLUX_KIT_EN` | Deepgram Flux TTS, model `flux-kit-en` | British masculine, young-adult hosted voice | Deepgram Voice Agent classroom persona `deepgram_kit` | `RIGHTS_PENDING` | confirm commercial classroom/public output scope under the active Deepgram plan; no local audio |
| `DEEPGRAM_FLUX_KAI_EN` | Deepgram Flux TTS, model `flux-kai-en` | Singaporean masculine, young-adult hosted voice | Deepgram Voice Agent classroom persona `deepgram_kai` | `RIGHTS_PENDING` | confirm commercial classroom/public output scope under the active Deepgram plan; no local audio |
| `DEEPGRAM_FLUX_HANNAH_EN` | Deepgram Flux TTS, model `flux-hannah-en` | United States / New York-oriented hosted voice configured for a fictionalized fashion-student persona | Deepgram Voice Agent classroom persona `deepgram_hannah` | `RIGHTS_PENDING` | confirm commercial classroom/public output scope under the active Deepgram plan; no local audio |
| `DEEPGRAM_FLUX_NAVEEN_EN` | Deepgram Flux TTS, model `flux-naveen-en` | India-oriented hosted voice configured for a fictionalized IIT Delhi technology-student persona | Deepgram Voice Agent classroom persona `deepgram_naveen` | `RIGHTS_PENDING` | confirm commercial classroom/public output scope under the active Deepgram plan; no local audio |

Catalog reference: `https://developers.deepgram.com/docs/flux-tts/voices.md`

The companion `deepgram_kai` classroom persona is aligned to Singapore: its
fictional birth and current city are Singapore, and its fictional university is
the National University of Singapore. These persona details do not add any
source-grounded identity claim, change the provider model ID, or change the
rights status recorded above.

For both sources, `identity_clone_allowed` is `false`,
`tts_reference_allowed` is `false`, and `tts_finetune_allowed` is `false`.
The source is called by its provider model ID at runtime; no reference WAV,
local original path, or personal consent record is claimed.

The same boundary applies to `DEEPGRAM_FLUX_HANNAH_EN` and
`DEEPGRAM_FLUX_NAVEEN_EN`. Hannah and Naveen are fictionalized classroom
personas whose biographies and interactional styles are stored separately in
`voices/personas/deepgram_hannah.json` and
`voices/personas/deepgram_naveen.json`. Their provider-hosted voice metadata
does not establish African American, New York, Indian, or any real-person
identity. The uploaded `Hannah.png` and `Naveen.png` files are visual
persona assets, not evidence of the voice source's identity.

For all four Deepgram classroom sources:

- `identity_clone_allowed: false`
- `tts_reference_allowed: false`
- `tts_finetune_allowed: false`
- `chatbot_output_allowed: pending provider-terms confirmation`
- `public_demo_allowed: pending provider-terms confirmation`

The raw provider settings remain under `prompts/raw_materials/`; the
runtime reads the corresponding persona profile from `voices/personas/` to
build the Layer 3 system-prompt content. These records are therefore the
provenance boundary used when the classroom chatbot is later activated.

## 5. Model별 사용 구분

| Model | 음성 사용 | 텍스트/대화 자료 | 현재 source 원칙 |
|---|---|---|---|
| Model 1 | 승인된 reference audio 기반 TTS | system prompt + Style Card/RAG | CHN_004 한 화자로 end-to-end baseline부터 시작 |
| Model 2 | 화자별 TTS LoRA | Model 1 prompt/RAG 유지 | clean student audio와 matching transcript가 충분하고 권리가 승인된 source만 사용 |
| Model 3 | 화자별 TTS LoRA | ELF dialogue/pragmatic data + Qwen **SFT/efficient SFT 또는 QLoRA** + RAG | read speech는 음향 참고용, dialogue corpus는 텍스트·화용 분석용으로 분리 |

## 6. 화자별 신규 기록 양식

새 음성을 추가할 때 다음 항목을 채운다.

```yaml
source_id:
persona_id:
voice_id:
display_label:
source_title:
source_provider:
source_url:
source_version:
access_date:
local_original_path:
local_processed_paths:
language_or_variety:
region_or_l1:
speaker_anonymized_id:
recording_type: spontaneous | interview | read_speech | classroom | other
transcript_path:
reference_clip_path:
reference_clip_transcript_path:
processing_script:
processing_date:
quality_notes:
consent_status:
license_status:
permitted_uses:
prohibited_uses:
identity_clone_allowed: false
voice_class_use_allowed:
tts_reference_allowed:
tts_finetune_allowed:
chatbot_output_allowed:
public_demo_allowed:
llm_text_training_allowed:
citation:
rights_evidence_path:
reviewer:
review_status:
notes:
```

## 7. 처리 기록

| 날짜 | `source_id` | 처리 | 산출물 | 판정 |
|---|---|---|---|---|
| 2026-09-12 | `ICNALE_SD_CHN_004` | pyannote diarization, 583 segments 생성 | RTTM, segments CSV | 원본 보존 |
| 2026-09-13 | `ICNALE_SD_CHN_004` | video/transcript 대조, role 확정 | role map, reviewed segments | `SPEAKER_00=Interviewer`, `SPEAKER_01=Student` |
| 2026-09-13 | `ICNALE_SD_CHN_004` | overlap·interviewer·일본어 구간 제외 | `STUDENT_CLEAN.wav`, exclusion log | reference clip 추출 전 |

## 8. TTS·LLM 권리 구분

- `CosyVoice v3-plus (Singapore)`: 현재 canonical TTS 경로. 승인된 reference audio만 입력한다. CosyVoice 2는 현재 프로젝트에 포함하지 않으며, v3-plus보다 우수하다고 전제하지 않는다.
- 새 voice source마다 target model별 voice enrollment를 한 번 수행해 `voice_id`를 발급하고 persona profile에 저장한다. 실시간 발화에서는 저장된 `voice_id`만 사용하며 reference WAV를 매번 전송하지 않는다.
- Deepgram TTS: 초기 hosted TTS smoke test 및 latency 비교용. reference voice clone을 의미하지 않는다.
- Qwen: 음성 자체를 학습하지 않는다. Qwen은 선택된 persona의 Style Card와 대화 정책을 사용한다.
- Alibaba Model Studio managed tuning을 사용하더라도 대상은 Qwen의 text layer이며, 음성 파일을 Qwen에 학습시키지 않는다. Qwen custom model API는 Deepgram STT와 Singapore CosyVoice v3-plus TTS 사이에 배치한다.
- Model Studio의 `SFT`(Supervised Fine-Tuning)는 승인된 ChatML text JSONL의 assistant 응답을 학습한다. 이는 CHN_004 음성의 음색이나 발음을 학습하는 절차가 아니다.
- Voice Agent 통합은 본 프로젝트의 primary 경로가 아니다. STT·Qwen text·TTS를 각각 분리해 측정하고 관리한다.
- 음성 source 권리와 Qwen 학습 자료 권리는 별도 기록한다.
- Model Studio에 업로드하는 전사·대화 자료는 source의 LLM training/third-party cloud processing 허가가 확인된 경우에만 사용한다.

## 9. 문서 관계

- 설계·아키텍처·Model 1–3 정의: `docs/1. GE-AI_technical-report.md`
- 음성 source·파일·권리·처리·reference clip 운영 기록: 이 문서 `voice-sources.md`
- 전체 의사결정 원장: `history.md`
