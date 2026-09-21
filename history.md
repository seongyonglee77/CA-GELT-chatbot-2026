# AI-design 작업 히스토리 — 3D Global Englishes Avatar 챗봇

> 이 파일은 `AI-design/` 폴더에서 발생하는 모든 작업(자료 파악, 설계 결정, 구현, 검증, 의사결정)을 **시간순으로 자동 누적 기록**하기 위한 단일 원장이다.
> 매 세션은 `### YYYY-MM-DD` 섹션을 하나 만들고, 그 안에서 (1) 오늘 한 일, (2) 변경/생성 파일, (3) 결정 사항, (4) 다음 우선순위를 기록한다.
> 본 파일 상단의 `## 메타` / `## 핵심 설계 SSOT` / `## 현재 상태`는 SSOT이므로 변경 시 근거를 같은 섹션 안에 명시한다.

---

## 메타

- **대상 시스템**: 최호성 교수님 본 수업 `Class B`에 투입될 **3D Global Englishes Avatar 챗봇** + 부속 **DDR 개발 연구 시스템**.
- **상위 문서** (본 파일과 동시 사용):
  - `/mnt/d/OneDrive/2_PhD/0_Pipeline/2_CA-GELT_Choe/Methods_260513.md` — Methods (탐색적 혼합연구)
  - `/mnt/d/OneDrive/2_PhD/0_Pipeline/2_CA-GELT_Choe/syllabus_class2_AI-chatbot.md` — Class B syllabus
  - `/mnt/d/OneDrive/2_PhD/0_Pipeline/2_CA-GELT_Choe/history.md` — IRB/전체 히스토리
  - `/mnt/d/OneDrive/2_PhD/0_Pipeline/2_CA-GELT_Choe/AI-design/ELF-LLM_conference-kor_linguistics/history.md` — 별개 SIOC 하위 프로젝트
- **로컬 시간**: Europe/London (UTC+01:00). 모든 timestamp는 로컬 시간 기준.
- **로컬 위치**: `/mnt/d/OneDrive/2_PhD/0_Pipeline/2_CA-GELT_Choe/AI-design/`

---

## 핵심 설계 SSOT (Single Source of Truth)

### 연구 분리 (DDR_3D_GE.md §4)
- **Study 1** — 본 수업 Class B 적용. **archived prior 4-model plan (Structured Corpus DB/RAG GE Avatar) 1개만** 사용. 학생에게 4개 모델 비교 노출 안 함.
- **Study 2** — DDR 개발 연구. **Model 1 generic / Model 2 system-prompt-conditioned / Model 3 corpus summary card / archived prior 4-model plan structured corpus DB/RAG** 4-model 비교.
- 두 연구가 같은 기술 코어(ASR→LLM→TTS→Avatar)를 공유하되, 처치/주장 경계는 분리.

### 6 화자군 (Korean 제외, Kachru 3-circle)
- **Model 1 (corpus 접근성 우선)**: US, British, Indian, Singapore, Nigerian, Japanese L1 English
- **Model 3 (지역 개연성 우선)**: US, British, Indian, Singapore, Philippine, Japanese/Thai L1 English
- 화자군당 4 variant (Neutral task / Collaborative peer / Service workplace / Corpus-structured RAG)
- 각 화자군은 **identity clone이 아니라 corpus-informed composite persona**

### 기술 코어 (DDR feasibility doc §10 + voice-cloning guide)
- **Primary**: `gemini-3.1-flash-live-preview` native audio-to-audio (PNU/부산대 SSOT, 2026-09-08)
- **Secondary**: Cascade `ASR → text LLM → TTS` (수치적 rate/pause 통제 필요 시 pilot/조건으로만)
- **TTS 옵션**: Cloud TTS / local OpenVoice V2 (MIT) / CosyVoice (Apache-2.0) / F5-TTS(weights CC-BY-NC, 검토 필요) / 호스티드 상용
- **Voice cloning**: 특정 개인 직접 섭외 + 별도 동의(prototype/demo/fine-tuning/ref-cond/audio-avatar/2차/보관/철회 분리). 공개 corpus는 identity clone source로 사용 금지.
- **Backend**: GAS Web App + Google Sheets (PNU-style). `LiveTranscript` (양방향 전사), `LiveMemory` (per-`(participant_id, model_id)` memory ledger)
- **Log schema**: `user_turn_end_ts / first_model_event_ts / first_audio_out_ts / response_end_ts / interruption_detect_ts / playback_stop_ts`, `response_onset_latency`, `interruption_stop_latency`

### PNU(부산대) AI-CA 기존 시스템 — 차용 가능 자산
- 4개 독립 앱: `live_base` / `model_1_vanilla` / `model_2_expert_prompt` / `model_3_expert_feedback`
- 포트 5173/5181/5182/5183
- 참가자 ID 체계 (`P01`, `P02`, `P03` — 본 수업은 ~40명으로 확장)
- `.env.local`: `VITE_GEMINI_API_KEY`, `VITE_APPS_SCRIPT_WEB_APP_URL`
- 통합 배포: `apps/participant-web` → `/model-1/`, `/model-2/`, `/model-3/` (Cloudflare Pages Direct Upload)
- ⚠ PNU 시스템은 **AI-CA storytelling 목적**. **Global Englishes representation은 미구현**이므로 그대로 재사용은 불가. 4-app 패턴·GAS+Sheets 백엔드·live base 분리·memory namespace 패턴은 차용.

---

## 인벤토리 (2026-09-08 1차 정리)

| 파일 | 역할 | 상태 |
|---|---|---|
| `0903 DDR_3D_GE.md` | DDR 마스터 설계 (6 화자군, archived prior 4-model plan, 2-연구 분리) | SSOT — 최신 |
| `1. 0903 3d-avatar-llm-chatbot-feasibility.md` | Two-stack + cascade + log schema + voice cloning ethics | SSOT — 최신 |
| `1. voice-cloning guide` | Live API 미세조정, Barge-in, SLA 기법 | 참조 |
| `1. 부산대 연구사례.md` | PNU SSOT (4 앱, GAS+Sheets, memory) | SSOT — 최신 |
| `1. 부산대 웹챗봇_제작가이드.md` | PNU 재현·운영 가이드 | SSOT — 최신 |
| `1. 3D참고자료-웹사이트.md` | 참고 GitHub: Educatian/ETHOBOT_ENG, wovencode/OpenMMO | 참고 |
| `참고_IAS-*.md` (3종, 6월) | IAS 워크숍 자료 | 보관 |
| `ref_image_video/1.jpg` | FORMA 오피스 전경 (외부 벤치마크) | 참고 |
| `ref_image_video/2.jpg` | FORMA NPC lineup (외부 벤치마크) | 참고 |
| `ref_image_video/3.jpg` | FORMA NPC walking (외부 벤치마크) | 참고 |
| `ref_image_video/bandicam 2026-09-06 18-08-36-182.mp4` | rIthobot (Jewoong Moon, LinkedIn) — HUMAN OVERSIGHT PROTOCOL/MODEL LAB 데모 | 참고 |
| `ref_image_video/bandicam 2026-09-07 22-11-00-975.mp4` | FORMA (Jewoong Moon, LinkedIn) — Instructional Designer Career Game NPC 테스트 | 참고 |
| `ELF-LLM_conference-kor_linguistics/` | SIOC 2026 하위 프로젝트 (별개) | 별도 관리 |

---

## 현재 상태

- ✅ IRB(ver3.0) 통과, 단일집단 QUAL-dominant exploratory mixed-methods + DDR
- ✅ Class A (발표형) / Class B (3D 아바타형) syllabus 완성
- ✅ 기술 feasibility 확인 (DDR + voice-cloning guide)
- ✅ PNU(부산대) Live API 기반 음성 챗봇 작동 코드 존재 (단, Global Englishes 용도 아님)
- ⏳ **archived prior 4-model plan (Structured Corpus DB/RAG) 인프라 미구축** — corpus feature 추출/태깅/검색 백엔드 없음
- ⏳ **3D avatar frontend 미선택** — 후보: Unity+LLMUnity / OpenAvatarChat / GMTalker / FORMA-유형 자체구축
- ⏳ **Voice cloning TTS 경로 미선택** — OpenVoice V2 vs CosyVoice vs 호스티드
- ⏳ **6 화자군 × Model 1–3 미확정**
- ⏳ **IRB에 voice cloning·3D embodiment·다화자군 노출 여부 미반영**
- ⏳ **Class B 1주차(2026-09 첫 주)까지 가용 MVP 정의 안 됨**

---

## 작업 일지

### 2026-09-08 (Tue, Europe/London)

#### 오늘 한 일
1. `AI-design/` 인벤토리 1차 정리 — 위 인벤토리 표 작성.
2. 외부 벤치마크 영상/이미지 식별: `ref_image_video/`는 사용자 자체 구현물이 아니라 **Jewoong Moon의 FORMA / rIthobot (AI NPC 학습 플랫폼) LinkedIn 데모**. 3D-NPC 환경이 이미 학습 플랫폼 형태로 구현·테스트되고 있음을 확인.
3. PNU(부산대) SSOT 4종 문서 통합 판독 — 4-app 패턴 / GAS+Sheets / memory namespace 패턴은 본 프로젝트에 차용 가능하나 Global Englishes representation 자체는 미구현 상태로 판단.
4. 우선순위 1순위 = `ref_image_video/` 콘텐츠 확인 → 완료.
5. `AI-design/history.md` 신설 — 본 파일.

#### 변경/생성 파일
- 생성: `AI-design/history.md` (본 파일)

#### 결정 사항
- (D1) `ref_image_video/` 외부 자료의 위치를 "참고 벤치마크"로 확정. 사용자 자체 구현 영상은 별도로 추가될 때까지 없음.
- (D2) PNU 4-app·GAS+Sheets·memory namespace 패턴을 차용하되 **Global Englishes representation layer는 별도 신규 설계**.
- (D3) 본 `history.md`의 SSOT 섹션은 작업 중 변경 시 같은 섹션 안에 사유 명시. 외부 `history.md`/conference 하위 history와 분리 유지.

#### 다음 우선순위 (다음 세션이 여기서부터 시작)
1. **6 화자군 Model 1–3 확정** — Class B 1주차(2026-09 첫 주, 사실상 immininent) 시한. ASEAN 개연성(B) vs corpus 접근성(A) trade-off 결정.
2. **3D avatar frontend 후보 비교표 작성** — `LLMUnity` / `OpenAvatarChat` / `GMTalker` / 자체 WebGL(PNU 패턴 확장) 4축 비교. 라이선스·latency·3D quality·브라우저 호환·avatar diversity·voice clone 통합성 항목.
3. **corpus 접근성 1차 점검** — DDR doc이 제시한 12 corpus 중 **transcript 접근 가능한 것**과 **audio까지 접근 가능한 것**을 분리 표로 정리. 음성 클로닝용 source audio 동의 절차 동시 점검.
4. **MVP (Class B 1주차용) 최소 기능 명세** — Study 1은 archived prior 4-model plan만 필요. "1주차에 최소 어떤 avatar 경험이 가능한가"를 1페이지로.
5. **IRB 보강 필요 여부** — voice cloning + 6 화자군 노출 + 3D embodiment가 IRB 본문에 어떻게 반영돼 있는지 점검. 필요 시 추가 심의/통보 결정.

#### 보류 (다음 우선순위가 끝난 뒤)
- archived prior 4-model plan ablation 실험 설계 (Study 2 DDR)
- Tasks 0–10 → 6 화자군 × scenario 매핑
- 평가척도(perceived authenticity / intelligibility / comfort / usefulness / stereotype) 문항화

---

### 2026-09-08 오후 (계속)

#### 오늘 한 일
1. AI-design/ 인벤토리 재확인 (PNU/DDR 5개 파일 라인 수 확인: 총 3743줄).
2. Cross-reference 점검 — PNU 두 문서가 `1. voice-cloning guide`를 정확히 참조 중 확인 (pnu-case-study.md L1317, pnu-build-guide.md L941).
3. **중심 문서 확정**: `1. 0903 3d-avatar-llm-chatbot-feasibility.md` (이하 "feasibility doc")를 모든 후속 통합의 SSOT로 확정.
4. **Feasibility doc 앞부분 §0 추가** — 사용자 확정 방향 4개(cascade 우선 / voice cloning 필수 / 단계적 fine-tuning / 웹→3D avatar→3D 공간 단계) + 적용 판정표 + 통합 대상 + 6일 sprint.
5. **3개 source doc 통합 계획 수립** (아래 결정 참조).
6. workspace tree 신규 파일 2개 확인: `bandicam 2026-09-08 17-00-47-780.mp4` (23.4MB), `KakaoTalk_20260908_133136873.mp4` (4.7MB) — 오늘자 녹화/캡처, 별도 확인 필요.

#### 변경/생성 파일
- 수정: `1. 0903 3d-avatar-llm-chatbot-feasibility.md` — §0. 현재 연구 적용 범위 추가 (34 lines, L7–L40)

#### 결정 사항
- (D4) **중심 문서 = feasibility doc**으로 확정. 다른 3개 source doc은 발췌·차용 후 archive.
- (D5) **연구 방향 4축 확정**:
  - cascade 모델 채택 (ASR→text LLM→TTS 분리형)
  - voice cloning 필수 (cascade가 필요한 직접 이유)
  - 단계적 fine-tuning (prompt + corpus profile)
  - 구현 단계: 초반=웹+3D avatar / 후속=3D 공간 NPC
- (D6) **제외 결정**: native audio stack native audio-to-audio / 다중 음성 동시 clone / Thai/Korean accent 동시 적용 — 본 연구 채택 안 함.
- (D7) **3 source doc 통합 계획** (아래 "통합 계획" 참조, 다음 세션부터 실행).

#### 통합 계획 (다음 세션 실행)

**Phase 1 — LLM 발화 정책 (voice-cloning guide → feasibility)**
- voice-cloning guide §3 (prompt+DSP 하이브리드) → feasibility 신규 §11 "LLM 발화 제어"
- voice-cloning guide §4 (SLA: Pause/Recast/Repair) → feasibility §11에 통합
- voice-cloning guide §1/§2 (Live Barge-in, Live latency) → **제외** (Live 안 씀)
- voice-cloning guide §5/§6 (cascade 필요성, Native vs Cascade) → feasibility §10에 이미 반영, 확인만
- voice-cloning guide §7 (TypeScript 예시) → 별도 code repo로 분리, 본 doc에는 핵심만 발췌

**Phase 2 — 백엔드/앱 구조 (PNU 두 문서 → feasibility)**
- PNU §10.9 (GAS+Sheets) → feasibility §10.9를 cascade용으로 구체화 (transcript 저장 흐름)
- PNU §1.2-1.3 (memory namespace) → feasibility 신규 §12 "메모리·로그 정책" (단, 우리 archived prior 4-model plan 4개로 재매핑)
- PNU §1.4 (앱 구조 4개) → feasibility §6 (MVP 경로)에 web 3D avatar 앱 구조로 변환
- PNU §1.5 (Cascade 보류) → **반대** — 우리는 cascade 채택, feasibility §10.1에 명시
- PNU §0 SSOT (Live API 동결, P01-P03) → **제외**

**Phase 3 — 운영 명세 추가**
- .env.local (VITE_GEMINI_API_KEY, VITE_APPS_SCRIPT_WEB_APP_URL) → feasibility 신규 §13 "환경변수·배포"
- npm install → typecheck → build → test 재현 순서 → feasibility §13

**Phase 4 — 6일 sprint 구체화**
- 신규 §14 "음성 1개 → 6 확장 템플릿"
- 신규 §15 "웹 3D avatar MVP"
- 신규 §16 "3D 공간 NPC (DDR 단계)"

**Phase 5 — 정리**
- 통합 완료된 3 source doc을 `archive/`로 이동 (출처 보존 위해 파일명 유지)
- history.md 갱신

#### 다음 우선순위 (이 다음 세션)
1. **Phase 1 (LLM 발화 정책) 통합 실행** — feasibility §11 신규 추가, voice-cloning guide §3·§4 발췌.
2. **Phase 2 (백엔드/앱 구조) 통합 실행** — feasibility §10.9 보강 + §12 신규.
3. **6일 sprint Day 1**: 음성 1개 후보 확정 + 동의 양식 작성.
4. workspace tree 신규 mp4 2개 (오늘자 bandicam + KakaoTalk) 확인 — 사용자 요청 시 진행.

#### 메모/리스크
- Cross-reference: PNU 두 문서 L1317, L941이 voice-cloning guide 파일명을 직접 참조. Phase 5에서 rename 시 같이 갱신 필요.
- 시간 압박: 6일 sprint, 음성 동의 + 녹음 + clone + cascade 작동까지 한 번에. 1음성 성공이 6화자군 확장의 전제.
- 신규 mp4 2개: 사용자가 오늘 캡처/녹화한 내용으로 추정. 별도 확인 필요 (본 task와 무관할 수도).

### 2026-09-08 저녁 (계속 2) — Phase 1·2 통합 실행

사용자 지시: "1번과 2번을 순차적으로 하자. 3번은 기각." → Phase 1(§11) + Phase 2(§10.9 보강 + §12) 순차 실행 완료. mp4 2개는 보류.

#### 오늘 한 일
1. **Phase 1 — §11 LLM 발화 제어 추가** (feasibility doc L548–L623, 76 lines)
   - voice-cloning guide §3 (prompt vs DSP) → §11.1 두 통제 레이어 표 + §11.2 권장 하이브리드
   - voice-cloning guide §4 (SLA: Pause, Recast, Repair) → §11.3.1–§11.3.4
   - §11.4 권장 System Prompt 골격 (Cascade용)
   - §11.5 DSP 측 구현 메모 (chunking, playbackRate, barge-in, STT 후보)
   - §11.6 구현 코드 위치 (별도 repo)
2. **Phase 2a — §10.9 보강** (feasibility doc L500–L533, 5줄 → 34줄)
   - §10.9.1 Cascade용 transcript 저장 흐름 (Live의 `turnComplete` vs Cascade의 chunk별 저장)
   - §10.9.2 Google Sheets 구조 (LiveTranscript/LiveMemory/VoiceConfig)
   - §10.9.3 GAS Web App 배포 (Code.gs 재배포, `/exec` env 노출)
   - §10.9.4 Voice cloning consent gate (Drive 경로, 철회 workflow)
3. **Phase 2b — §12 메모리·로그 정책 추가** (feasibility doc L625–L714, 90 lines)
   - §12.1 archived prior 4-model plan 모델 격자 표 (Class B는 archived prior 4-model plan만, DDR은 archived prior 4-model plan)
   - §12.2 memory namespace (`participant_id + model_id`)
   - §12.3 Apps 구조 (web + 3D avatar, 포트 5173/5181-5184)
   - §12.4 Log schema (Cascade 강제 6개 timestamp + 2개 latency 지표)
   - §12.5 version 관리 (prompt/model/voice/corpus/consent 5종)
   - §12.6 Build & 재현 순서 (npm install → env → Apps Script deploy → typecheck/build/test → turn 저장·재조회 검증)

#### 변경/생성 파일
- 수정: `1. 0903 3d-avatar-llm-chatbot-feasibility.md`
  - 482 lines → 715 lines (+233)
  - §11 신규 (76 lines)
  - §10.9 보강 (29 lines net)
  - §12 신규 (90 lines)

#### 결정 사항
- (D8) **feasibility doc이 본 연구의 단일 SSOT**으로 자리잡음. 다른 3 source doc은 발췌 출처로만 참조.
- (D9) **Class B 본 수업 = archived prior 4-model plan 단일 모델**, DDR = archived prior 4-model plan — §12.1에 명시.
- (D10) **archived prior 4-model plan 포트**: 5181/5182/5183/5184 (PNU 패턴 차용, archived prior 4-model plan 신규).
- (D11) **Voice cloning consent gate**는 IRB-approved 동의서 양식을 사용하고 Drive 경로 + 철회 workflow 포함 — §10.9.4에 명시.

#### 다음 우선순위 (이 다음 세션)
1. **6일 sprint Day 1**: 음성 1개 후보 확정 + 동의 양식 작성 (가장紧迫).
2. **Phase 3 — §13 환경변수·배포**: feasibility §13 신규, .env.local 운영 가이드 (Phase 1·2에서 이미 §12.6에 일부 포함, 별도 §13으로 분리 검토).
3. **Phase 4 — §14·§15·§16**: 음성 1개 → 6 확장 템플릿 / 웹 3D avatar MVP / 3D 공간 NPC (DDR 단계) — 6일 sprint 진행하면서 동시에 작성.
4. **Phase 5 — archive 정리**: 통합 완료 후 3 source doc → `archive/` 이동 + PNU 두 문서 cross-ref(L1317, L941) 갱신.
5. mp4 2개 (오늘자 bandicam + KakaoTalk) 확인 — 사용자 요청 시 진행.

#### 메모/리스크
- 파일이 715 lines로 성장. §0–§12 모두 SSOT. 다음은 §13(운영)·§14–§16(sprint)로 진행.
- §10.9가 두 번 등장하는 외관상 중복(`### 10.9 저장` + `### 10.9 근거·재검증 링크`) — 원본 doc의 numbering 실수. 추후 §10.9.5로 통합 검토.
- 시간 압박: 6일 sprint D-6. 음성 후보·동의·녹음·clone·cascade 작동까지 5단계 동시 진행 필요.

### 2026-09-08 저녁 (계속 3) — Day 1 준비 + 보수적 정리

사용자 지시:
1. 음성 후보 선정 — 6개 국가 고정 아님, available corpus 기반
2. 중심 문서 보수적 정리 — 제한적, 순서 조정 허용
3. (보류) mp4 2개

#### 오늘 한 일
1. **중심 문서 보수적 정리** (`1. 0903 3d-avatar-llm-chatbot-feasibility.md`, 715 → 727 lines):
   - **§0.5 섹션 적용 가이드 추가** (17 lines) — 각 섹션의 적용 상태(✓ 적용 / △ 부분 / ✗ 대체 예정)를 한 표로 명시
   - **§4·§6·§8·§9에 1-line historical 메모** 추가 (각 2 lines, 총 8 lines) — 2026-08 작성 시점의 outdated 부분을 명시
   - **§10.9 중복 numbering 수정** — 두 번째 `### 10.9 근거·재검증 링크`를 `### 10.10`으로 정정
   - **순서 조정 없음** (현재 numbering이 자연스러워 그대로 유지)
2. **음성 후보 1차 평가** — DDR doc corpus 후보 + voice class ethics 기반 (아래 결정 참조).

#### 변경/생성 파일
- 수정: `1. 0903 3d-avatar-llm-chatbot-feasibility.md`
  - 715 → 727 lines (+12)
  - §0.5 신규, §10.10 정정, §4·§6·§8·§9 메모 추가

#### 결정 사항
- (D12) **중심 문서 보수적 정리 완료**: §0.5 적용 가이드 + historical 메모 + §10.10 numbering 정정. 내용 삭제는 하지 않음 (사용자 지시: 제한적).
- (D13) **음성 후보 Day 1 선정안** (다음 단계 결정 필요):
  - **1순위**: L2-ARCTIC Japanese L1 English speaker + OpenVoice V2 (MIT) voice class
    - 이유: 가장 쉬운 접근, DDR 6화자군 중 1개 즉시 활용, voice class로 ethics 안전, 6일 내 작동 보장
  - **2순위** (Day 2-3 진화): 직접 섭외한 동의 화자 + IRB-approved 동의서
  - **3순위** (대안): ICNALE Spoken Dialogue 또는 ICE-Nigeria/Singapore
- (D14) **identity clone 금지, voice class만 허용** — feasibility §10.6에 이미 명시, Day 1 결정으로 재확인.

#### 다음 우선순위 (이 다음 세션)
1. **음성 후보 1순위 확정 + 동의서 양식 초안** — L2-ARCTIC Japanese + voice class 접근이 OK인지 사용자 결정 요청
2. **§10.10 (구 §10.9 중복)을 §11.7 "참조 링크"로 재배치 검토** (현재 §10.10은 doc 마지막에 위치, §11·§12와 묶는 게 더 자연스러울 수 있음)
3. **Phase 3 — §13 환경변수·배포**: .env.local 운영 가이드 별도 §13 분리
4. **Phase 4 — §14·§15·§16**: 6일 sprint 진행하며 작성 (음성 1→6 템플릿, 웹 3D avatar MVP, 3D 공간 NPC)
5. **mp4 2개** — 보류 유지

#### 메모/리스크
- 6일 sprint D-5 (한국 시간 기준 다음 주 월요일 D-day). 1음성 작동이 6화자군 확장의 전제.
- L2-ARCTIC 라이선스: "voice class" 용도 OK, "identity clone"은 명시적 금지. Day 1 결정 시 IRB 검토 필요할 수 있음.
- OpenVoice V2 라이선스: MIT. 상업적 연구/논문 배포 가능.
- ICNALE 라이선스: 연구용 OK이지만 chatbot 음성 출력용 별도 확인 필요.

### 2026-09-08 저녁 (계속 4) — 비-네이티브 음성 코퍼스 추가 조사 + §11.7·§13 추가

사용자 지시:
1. item 1 다시 조사 — 음성 source available corpus 기반
2. §10.10 → §11.7 이동 (item 2)
3. §13 신규 (item 3)
4. mp4 2개 — 보류

#### 오늘 한 일

**A. 비-네이티브 영어 음성 코퍼스 추가 조사 (web_search + direct URL fetch)**

| 코퍼스 | 라이선스 | 화자 수 / L1 | 특징 | URL |
|---|---|---|---|---|
| **Speechocean762 (SLR101)** | 무료 (상업/비상업) | 250 non-native, **모두 Mandarin** | pronunciation scoring 5단계 annotation, HuggingFace `mispeech/speechocean762` | https://www.openslr.org/101/ |
| **MRPL2 (Zenodo, 2026)** | **CC BY 4.0** | 23명 / **14 L1** (Cantonese, Thai, Tamil, Urdu, Azeri, Bulgarian, French, Italian, Kurdish, Persian, Polish, Portuguese, Romanian, Spanish) | MDD/ASR/phonetic analysis, 48k+16kHz, CMU Arctic prompts (public domain) | https://doi.org/10.5281/zenodo.20365864 |
| **Nigerian English (SLR70)** | (확인 필요) | crowdsourced high-quality | Outer Circle 다양성 | https://www.openslr.org/70/ |
| **LibriTTS-R (SLR141)** | (LibriSpeech 파생) | LibriVox 기반 English | sound quality improved, TTS용 standard | https://www.openslr.org/141/ |
| **Hi-Fi TTS (SLR109)** | (확인 필요) | multi-speaker English | TTS training | https://www.openslr.org/109/ |
| **CML-TTS (SLR146)** | (확인 필요) | multilingual low-resource | TTS training, 다양한 L1 | https://www.openslr.org/146/ |
| **BibleTTS (SLR129)** | (확인 필요) | multilingual African | large, high-fidelity | https://www.openslr.org/129/ |

**B. Voice cloning 모델 최신 상태 재조사**

| 모델 | 라이선스 | native multilingual | cross-lingual clone | 비고 |
|---|---|---|---|---|
| **OpenVoice V2** | **MIT** (April 2024) | EN/ES/FR/ZH/JP/KO ✓ | ✓ tone color + rhythm/pause/intonation control | zero-shot, 1-5초 reference |
| **CosyVoice 2** | **Apache-2.0** (Alibaba FunAudioLLM) | ZH/EN/JP/KO/Yue ✓ | ✓ (강력) | speaker identity control via instructions, emotion/style control, speaker interpolation |
| F5-TTS | code MIT, weights **CC-BY-NC** | multilingual | ✓ | commercial 사용 시 weights 재검토 |
| XTTS v2 | (확인 필요) | multilingual | ✓ | Coqui project |
| commercial TTS Turbo v2.5 | 상용 | multilingual | ✓ | 품질 최상, 비용 ↑ |

**C. 통합 권장 (item 1 재조사 결과)**

음성 source 후보 갱신 (가용성·다양성·라이선스 중심):
1. **★★★ MRPL2 Cantonese L1 English (CAF01)** — CC BY 4.0, 6화자군 Expanding Circle(Asian)에 즉시 활용 가능, 14 L1 다양성 → 6화자군 전체 확장 시 동일 corpus 재활용
2. **★★★ MRPL2 Thai L1 English (THM01)** — CC BY 4.0, Asian ELF 다양성
3. **★★ speechocean762 Mandarin L1** — 무료 상업 가능, 250명 다양성, 단 Mandarin only
4. **★★ SLR70 Nigerian English** — Outer Circle 다양성
5. **★ L2-ARCTIC Japanese L1** — 기존 후보, MRPL2 대비 다양성↓
6. 직접 섭외 동의 화자 — 윤리적 최선, 시간 부담

Clone 모델 후보 갱신:
- **★★★ CosyVoice 2 (Apache-2.0)** — cross-lingual 강점 (e.g., Cantonese audio → English output), emotion/style/instruction control
- **★★ OpenVoice V2 (MIT)** — zero-shot 1-5초 reference, 한국어/일본어 native
- 둘 다 동시에 비교 후 선택

**D. 문서 편집**
- **§10.10 → §11.7 이동**: 13 lines 삭제 + 18 lines 신규 (§11.7 참조 링크, OpenVoice V2·CosyVoice 2·speechocean762·MRPL2·SLR70 링크 추가)
- **§13 신규**: 99 lines (§13.1 환경변수, 13.2 Apps Script 배포, 13.3 로컬 빌드, 13.4 통합 배포, 13.5 운영 체크리스트, 13.6 트러블슈팅)

#### 변경/생성 파일
- 수정: `1. 0903 3d-avatar-llm-chatbot-feasibility.md`
  - 727 → 845 lines (+118)
  - §10.10 삭제 (13 lines)
  - §11.7 신규 (18 lines, CosyVoice 2 등 신규 링크 포함)
  - §13 신규 (99 lines)

#### 결정 사항
- (D15) **음성 source 1순위 갱신**: MRPL2 Cantonese L1 English (CAF01) — CC BY 4.0, Asian ELF 다양성, 14 L1 diversity
- (D16) **Clone 모델 1순위 갱신**: **CosyVoice 2** (Apache-2.0) — cross-lingual 강력, emotion/style/instruction control. OpenVoice V2(MIT)는 2순위 backup.
- (D17) **음성 source 다양성 전략**: MRPL2 단일 corpus에서 6화자군 모두 (Cantonese/Thai/Tamil/Urdu/Spanish/Italian 등) 추출 가능 → 6음성 1번에 통합 가능 (corpus 통일성)
- (D18) **§13 환경변수·배포 추가**: §12.6의 build 명령을 운영 차원으로 확장. Day-by-Day 체크리스트 포함.

#### 다음 우선순위 (이 다음 세션)
1. **음성 source 최종 확정 (CosyVoice 2 + MRPL2 vs OpenVoice V2 + L2-ARCTIC)** — 사용자 결정 요청
2. **§14·§15·§16 신규**: 6일 sprint 진행하며 작성 (음성 1→6 템플릿, 웹 3D avatar MVP, 3D 공간 NPC)
3. **Phase 5 — archive 정리**: 3 source doc → `archive/` 이동 + PNU 두 문서 cross-ref(L1317, L941) 갱신
4. mp4 2개 — 보류

#### 메모/리스크
- MRPL2는 **2026 release**, Zenodo DOI로 영구 보존. 안정성 OK.
- speechocean762는 **Mandarin only** — Asian ELF 다양성에는 부족, 단 250명 다양성은 강점.
- CosyVoice 2는 **Alibaba** 모델. 중국 기업 모델이지만 Apache-2.0 라이선스로 오픈소스. 연구용 안전.
- MRPL2의 Thai L1 화자(THM01)는 **self-recorded** 표시 — 녹음 품질 일관성 약할 수 있음. 1순위는 Cantonese(CAF01) 권장.
- 한국 시차: 현재 18:30 UK, 한국 시간 02:30 다음날. D-day 다음 주 월요일 (D-5).

### 2026-09-08 저녁 (계속 5) — §10.10 Global Englishes 확장 + Outer/Inner 비-US 추가

사용자 지시:
1. §10.10 + §11.7에 non-native English 조건 적용 (계속 4에서 일부 누락)
2. Outer Circle (Nigeria, HK, Singapore 등) 추가 — 영어권이 아니지만 Outer Circle인 경우
3. Inner Circle 비-US (호주 등) 추가 — 미국 영어 외 다른 영어권

#### 자가 검증 (계속 4의 self-audit)

7개 후보 중 **non-native English 조건 실제 충족은 2개뿐**:
- ✅ Speechocean762 (모두 Mandarin L1)
- ✅ MRPL2 (14 L1 모두 non-native)
- ❌ SLR70 Nigerian English — 이전엔 제외했으나 사용자 지시로 **재포함** (Nigerian English 화자는 L1 Yoruba/Igbo/Hausa, 영어는 L2 — nativized variety지만 화자 기준 L2)
- ❌ LibriTTS-R, Hi-Fi TTS — native US English (다양성 결여)
- ❌ CML-TTS, BibleTTS — 다국어 저자원 언어 (영어 화자군 무관)

#### 오늘 한 일 — §10.10 Global Englishes 8-화자군 확장

**§10.10.1 filter 확장**: 
- Inner Circle (US, UK, **Australia**, NZ, Ireland, Canada) — native variety 다양성
- Outer Circle (Nigeria, Singapore, India, Philippines, **Hong Kong**, Malaysia) — L1 비영어 + 영어 사용
- Expanding Circle (Japan, Thailand, Vietnam, China) — L1 비영어 + 영어 L2 학습
- Korean 제외

**§10.10.2 inventory 확장**:
- Inner Circle 7개 코퍼스 (SLR45, SLR83, BNC, ICE-GB, LibriTTS-R, AusTalk/CV-AU, Hi-Fi TTS)
- Outer Circle 10개 코퍼스 (**SLR70 Nigerian English**, ICE-Nigeria, Singapore NCS, ICE-Singapore, ICE-India, ACE, ICE-Philippines, HK English, VOICE 3.0, YCSEP)
- Expanding Circle 8개 코퍼스 (MRPL2, Speechocean762, L2-ARCTIC, ICNALE, ELFA, TLC, LINDSEI, CSLU)
- 보조 (Common Voice, SLR109)

**§10.10.3 Day 1 권장 갱신**: 화자군 8개로 확장 (Step A: MRPL2 Cantonese, Step B: SLR70 Nigerian, Step C: SLR83 UK)

**§10.10.5 라이선스 점검 확장**: Outer Circle (SLR70, ICE-Nigeria, Singapore NCS, ICE-India/Singapore/Philippines, HK English) + Inner Circle (SLR45, SLR83, BNC, ICE-GB) 추가

**§10.10.6 신규**: 화자군 ↔ 코퍼스 매핑 표 (8 화자군 × 1·2순위 코퍼스)

**§11.7 참조 링크 확장**: 4개 카테고리 (API/TTS / Inner Circle / Outer Circle / Expanding Circle) — 각 코퍼스 URL 완전 정리

#### 변경/생성 파일
- 수정: `1. 0903 3d-avatar-llm-chatbot-feasibility.md`
  - 845 → 1002 lines (+157)
  - §10.10 제목/intro 변경 ("Non-native / L2 English" → "Global Englishes")
  - §10.10.1 filter 확장 (5 lines → 25 lines, 화자군 분류 표)
  - §10.10.2 inventory 확장 (13 rows → 28 rows, 4 subsections)
  - §10.10.3 Day 1 권장 갱신 (Expanding/Outer/Inner 3-track)
  - §10.10.5 라이선스 점검 확장 (5 → 9 코퍼스)
  - §10.10.6 화자군 매핑 표 신규 (15 lines)
  - §11.7 참조 링크 확장 (8 → 32 links, 4 카테고리)

#### 결정 사항
- (D19) **§10.10 scope = Global Englishes 8 화자군** (Inner Circle 비-US + Outer Circle + Expanding Circle)
- (D20) **8 화자군 확정**: US, British, Australian (Inner) + Nigerian, Singapore, Indian (Outer) + Japanese, Thai (Expanding)
- (D21) **Day 1 권장**: Step A MRPL2 Cantonese → Step B SLR70 Nigerian → Step C SLR83 UK (Inner Circle 다양성 검증)
- (D22) **모든 화자군 동일 pipeline** (CosyVoice 2 + reference audio 5-15초 + voice class 라벨), swap은 `voice_id`만 변경

#### 다음 우선순위 (이 다음 세션)
1. **음성 source 최종 확정** (사용자 결정 요청) — Day 1 Step A/B/C 중 어디부터 시작?
2. §14·§15·§16 신규 (음성 1→6 템플릿, 웹 3D avatar MVP, 3D 공간 NPC)
3. Phase 5 — archive 정리 + PNU cross-ref 갱신
4. mp4 2개 — 보류

#### 메모/리스크
- SLR70/ICE-Nigeria의 실제 다운로드 가능성과 라이선스 — **즉시 확인 필요** (Step B Day 1 시작 전)
- AusTalk / SLR Australian — openslr에 별도 SLR 없을 수 있음. Common Voice AU subset으로 대체 검토.
- Hong Kong English (HKUST/HKUE) — 검증 필요. 실제 다운로드 URL/접근성 확인 안 됨.
- 시간 압박 D-5 (한국 시간). 화자군 8개를 6일 안에 다 clone하는 것은 무리 — **archived prior 4-model plan prototype 1개 + 음성 swap 템플릿 검증**이 핵심 목표.
- Inner Circle native English (US/UK/Australian)는 Kachru native circle로 본 연구 다양성 목적에 부분 부합. **대부분 Outer/Expanding Circle 화자군이 다양성 기여의 핵심**.
### 2026-09-08 저녁 (계속 6) — §11.7 inline 통합 + Step C 책임 경계

사용자 지시 2건 정리.

(1) Step C (SLR83 UK) 네가 할거야? 책임 경계: SLR83 license 확인 가능, CosyVoice 2 셋업 코드 작성 가능, reference audio 추출 가능, 실제 다운로드 시도 가능, clone 실행 불가능, 음성 청취 검증 불가능. 결론: 사전 검증 + 셋업 코드는 내가 하고, 실제 실행은 사용자.

(2) §11.7 분리 어색 → inline 링크 통합 완료. 모든 참조가 해당 내용 직후에 위치.

변경 파일: 1. 0903 3d-avatar-llm-chatbot-feasibility.md. 1002 → 1001 lines. §11.7 별도 절 삭제. §10.10.2 각 subsection에 inline 참조 추가. §11.6 다음에 API/TTS inline 참조 추가.

결정: (D23) §11.7 별도 절 폐지. (D24) Step C 사전 검증은 내가, 실행은 사용자.

다음: Step C 사전 검증 시작, 음성 source 최종 확정, §14·§15·§16 신규, Phase 5 archive 정리, mp4 2개 보류.
### 2026-09-09 (Wed, 새벽) — §10.10.0 접근성 분류 + 사용자 액션 체크리스트

사용자 지시:
1. voice cloning 사용 음성 (voice class) 즉시 가능 6개국 정리
2. per-application 신청 필요 코퍼스 정리
3. 통보 필요 (IRB / license) 분리
4. §10.10과 §10.10.1 사이에 삽입, 링크 포함
5. 사용자가 직접 처리 (신청/통보)

#### 발견: 중심 문서 파일명 변경

사용자가 2026-09-08 19:01에 `1. 0903 3d-avatar-llm-chatbot-feasibility.md`를 `1. GE-AI_technical-report.md`로 **rename** (50.1KB, 1002 lines, 내용 동일). 이후 작업은 새 파일명으로 진행.

#### §10.10.0 추가 내용

즉시 가능 (Voice class 6개국):
1. Thailand — MRPL2 THM01 (CC BY 4.0)
2. China — Speechocean762 (SLR101)
3. Nigeria — SLR70 + ICE-Nigeria
4. Japan — L2-ARCTIC
5. US — SLR45
6. UK — SLR83

신청 필요 (per-application): Singapore NCS, ICE-Singapore/India/Philippines/GB, ACE, BNC, VOICE 3.0, ELFA, TLC, HKUE/HKUST

통보 필요: 한국외대 IRB voice cloning 추가, L2-ARCTIC/SLR70/ICE-GB chatbot 사용 license inquiry

사용자 액션 체크리스트 (D-1):
1. 즉시 다운로드 (6개국)
2. 신청 메일 발송 (Singapore/India/Philippines/UK/ACE/VOICE/ELFA/TLC/HK)
3. IRB voice cloning 통보 (한국외대)
4. CosyVoice 2 셋업

#### 변경/생성 파일

수정: 1. GE-AI_technical-report.md
  1002 → 1064 lines (+62)
  §10.10.0 신규 (즉시 가능 / 신청 / 통보 / 액션 체크리스트)

#### 결정 사항

(D25) §10.10.0 = 접근성 분류 + 사용자 액션 체크리스트. §10.10과 §10.10.1 사이에 삽입.

(D26) voice class 즉시 가능 6개국 확정: Thailand, China, Nigeria, Japan, US, UK. 1음성 시작 추천 = MRPL2 THM01 (CC BY 4.0).

#### 다음 우선순위

1. 사용자가 직접 즉시 다운로드 + 신청 + 통보 시작 (D-1)
2. CosyVoice 2 셋업 (저는 코드/스크립트 작성 가능)
3. Step C (SLR83 UK) 사전 검증
4. §14·§15·§16 신규 (음성 1→6 템플릿, 웹 3D avatar MVP, 3D 공간 NPC)
5. Phase 5 archive 정리

#### 메모/리스크

파일명 변경 (feasibility → GE-AI_technical-report) 사용자가 결정. history.md 및 본 history.md의 모든 참조는 새 파일명으로 통일.
D-4 한국 시간 (현재 00:15 다음날 = Wed 아침). D-day 다음 주 월요일.
사용자 수면 후 즉시 다운로드 가능 (자동화 가능 시 user-side script).
### 2026-09-09 (Wed, 새벽) — (a) 신청/통보 양식 + (b) §10.10.7 확장 옵션

사용자 지시 (a) 신청/통보 양식 별도 문서, (b) 추가 voice class L1 확장 옵션 정리.

(a) 별도 문서 생성

신규 파일: 2. corpus-application-notification-templates.md (12.4KB).

구조: Part 1 신청 8종, Part 2 통보 4종, Part 3 발송 체크리스트, Part 4 첨부.

각 양식 포함: Voice class 명시 (identity clone 금지), 5축 동의 항목 §10.6, IRB placeholder, 3년 보존, Citation 약속.

(b) §10.10.7 신규
1. GE-AI_technical-report.md 1064 to 1133 lines (+69).

섹션 10.10.7 추가 L1 확장 옵션:
MRPL2 단일 14 L1로 21개국 voice class 추출 가능 (CC BY 4.0).
L2-ARCTIC Korean 제외 6 L1.
Speechocean762 Mandarin only.
Common Voice 다국어 필터링 CC0.
5개 확장 시나리오.

결정

(D27) 별도 템플릿 문서 신설. 12개 양식 + 체크리스트.
(D28) MRPL2 단독 21개국 voice class 가능.
(D29) 확장 시나리오.

다음

1. 사용자가 템플릿 발송 (D-1 오전).
2. CosyVoice 2 셋업 코드 (저자).
3. Step C SLR83 사전 검증.
4. §14-§16 신규.

D-4 KST, D-day 다음 주 월요일 = D-5.
### 2026-09-09 (Wed, 오전) — 마무리: (a)/(b) 상태 확인 + voice cloning layer 분리 설명

사용자 지시: 오늘 작업 마무리. history.md에 현재 상태 기록 + 내일 보고용 템플릿 준비.

#### 오늘 사용자 질문 3건 + 답변

(1) (b) 문서 정리 상태?
답변: 이미 정리됨. 1. GE-AI_technical-report.md 섹션 10.10.7 (MRPL2 14 L1, L2-ARCTIC 6 L1, Speechocean762, Common Voice, 5개 시나리오).

(2) 세션 리포트 요청.
답변: 파일 상태 (3개), 누적 결정 (D25-D29), 다음 단계 (사용자 vs 저자, D-1 to D-6).

(3) Voice cloning이 말투/대화 방법까지 복제하나? 텍스트 코퍼스 기반인가?
답변:
- Voice cloning (TTS-only) = 음성/음색/억양/리듬/pause 만 복제. 대화 방법은 복제 안 함.
- Layer 분리: LLM (text layer) = 어휘/문법/담화표지/수리전략, TTS (acoustic layer) = 음색/성조/속도/pause/accent.
- Voice cloning 기술 = audio 기반 (음성 데이터 → 음성 합성). 텍스트 코퍼스는 직접 사용 안 함.
- 그러나 본 프로젝트 §10.10.4 + 섹션 11은 corpus-informed LLM prompt로 어휘/담화는 LLM layer에서 처리 (별도 텍스트 코퍼스 사용).
- Cascade 파이프라인: ASR (Whisper/Deepgram) → Qwen 3.6 (LLM + corpus prompt) → CosyVoice 2 (TTS, audio 기반 voice clone) → 3D avatar.
- identity clone + style clone 둘 다 하려면 4-6주 작업 (음성 녹음 + transcript 수집 + LLM fine-tune/RAG + TTS 학습 + 통합). 우리는 voice class + prompt 기반이므로 합리적 시간 내 가능.

#### 변경/생성 파일

없음 (보고 및 Q&A만 수행, 문서 편집 없음).

#### 결정 사항

(D30) Voice cloning layer 분리 SSOT 확립:
- 음성 layer (TTS, CosyVoice 2): acoustic features only (timbre/intonation/rhythm/pause)
- 대화 layer (LLM, Qwen 3.6 + corpus prompt): lexis/syntax/discourse/repair/pragmatics
- 우리 cascade는 두 layer 분리 운용. 각 layer별 데이터 타입 분리 (audio vs text).
- 본 cascade 설명은 섹션 10.5 (아키텍처 권고) + 섹션 10.10.4 (corpus-informed style profile) + 섹션 11 (LLM 발화 제어)에 이미 반영됨.

(D31) 내일 보고용 템플릿 결정 (아래 참조).

#### 다음 우선순위 (사용자 일시정지, D-4 KST 종료)

1. 사용자 휴식. 내일 새벽/오전 재개.
2. D-day 다음 주 월요일 (D-5 KST). 발송 가능한 모든 신청 메일 회신 deadline.
3. Class B 1주차 (9월 셋째 주)까지 archived prior 4-model plan prototype + 6화자군 음성 작동 필수.

#### 메모/리스크

오늘 작업 종료 시점 (한국 시각 9월 9일 09:39):
- 사용자가 직접 처리할 항목: 2. corpus-application-notification-templates.md의 12개 양식 발송 (D-1 ~ D-2)
- 저자 처리 대기: CosyVoice 2 셋업, MRPL2 reference audio 추출, cascade 통합, Step C 검증, 섹션 14-16 신규
- 회신 timeline: per-application corpus는 1주 ~ 1개월 (보수적으로 봐야 함). 즉시 가능 6개국만으로 D-5까지 1차 작동 가능.

---

### 2026-09-10 (Thu, 예정) — 내일 보고용 템플릿

사용자가 내일 "보고해" 명령 시 아래 구조로 자동 리포트.

#### 내일 보고 템플릿 (사용자가 "보고해" 또는 "상태 보고" 시 적용)

Part A: 어제 마지막 보고 내용 (voice cloning layer 분리)
(1) Voice cloning layer 분리 (음성 layer vs 대화 layer)
(2) 텍스트 코퍼스 vs audio 데이터 분리
(3) 본 cascade 구조 설명 (ASR → LLM + corpus prompt → TTS → avatar)
(4) Identity clone + style clone vs 우리 voice class + prompt 비교 (4-6주 vs 합리적 시간)

Part B: 작업 상태 (현재 진행)
1. 파일 상태: 1. GE-AI_technical-report.md (1133 lines), 2. corpus-application-notification-templates.md (12.4KB), history.md
2. SSOT 결정: D25-D29 (사용자 액션 체크리스트, 6개국 확정, 템플릿 신설, MRPL2 21개국, 확장 시나리오)
3. 사용자 처리 상태: 템플릿 발송 진행 상황 (어제 시작했으면 그 결과)
4. 저자 처리 상태: CosyVoice 2 셋업, MRPL2 reference 추출 등 어제 이후 진행

Part C: 할 일 요약 (우선순위 순)
(1) 사용자 처리: 템플릿 발송 결과 확인, IRB 회신 확인, 다운로드한 6개국 corpus
(2) 저자 처리: CosyVoice 2 셋업, MRPL2 reference 추출, cascade 통합, Step C 검증
(3) 대기: per-application corpus 회신, IRB 추가 통보 회신
(4) 후속: 섹션 14-16 신규, Phase 5 archive 정리

Part D: D-day 카운트다운
- D-4 (오늘) / D-3 / D-2 / D-1 / D-0 (D-day 다음 주 월요일)
- 현재 한국 시간 기준 D-day까지 남은 시간

Part E: 메모/리스크 갱신

내일 보고 시 자동 적용 방식: 사용자가 보고를 요청하면 history.md의 Part A-D 구조를 그대로 활용하여 1) 어제 내용 요약 2) 현재 상태 3) 할 일 4) D-day 카운트다운 순으로 정리.

#### 메모/리스크

사용자 일시정지 후 재개 시 history.md 자동 활용 약속:
- 내일 보고 명령 시 Part A-D 구조 자동 적용
- history.md의 누적 결정 D25-D31 + 새 결정 추가
- 작업 진행/이슈 발생 시 즉시 history.md에 갱신

### YYYY-MM-DD (세션 템플릿)

#### 오늘 한 일
1.

#### 변경/생성 파일
- 생성:
- 수정:

#### 결정 사항
- (Dn) ...

#### 다음 우선순위
1.
2.

#### 메모/리스크
-
### 2026-09-09 (Wed, 오후) — §3.3 voice cloning 4-레이어 verdict + LLM fine-tuning 권고

사용자 지시: 음성 클로닝 텍스트 영역 발화 스타일(억양/운율/말투/문법/말습관) 모델링 방법을 autoresearch 미션으로 정리하고, 1. GE-AI_technical-report.md §3.3에 반영.

#### 오늘 한 일
1. **Autoresearch 미션 수행** (slug: voice-cloning-text-style-2026, web mode)
   - DuckDuckGo + Semantic Scholar + Scopus 모두 IP-level 429 (key 정상이나 IP 차단)
   - 우회: arXiv direct API + ISCA 아카이브 + GitHub README + 우리 문서 cross-reference
   - 16개 핵심 논문 + 4개 GitHub repo + 1 내부 verdict 비고
   - receipt 10bce93e 발행, mission cleared
2. **1. GE-AI_technical-report.md §3.3 재작성** (4-레이어 화자 동일성 보존 프레임워크)
   - §3.3 헤더 갱신 + 4-레이어 매트릭스 표
   - §3.3.1 L3 Lexis-Syntax (Style Card + few-shot + RAG + PEFT/LoRA, JSON v1 스키마 예시)
   - §3.3.2 L4 Discourse-Habit (explicit token notation v1, 6편 논문 매트릭스)
   - §3.3.3 L2-text (5편 prosody LLM-side 방법)
   - §3.3.4 L1 Timbre (참고)
   - §3.3.5 인용 summary
   - §3.3.5a 주요 venue map (Tier 1/2/3 × 학회·저널)
   - §3.3.6 조사 한계
   - §3.3.7 후속 보강 권고 6개
   - §3.3.7a 실현 가능성 평가 + 필요 자원 + 원본 요청 후보
   - §3.3.7b 권장 작업 우선순위 (1주/2주/보류)
   - §3.3.7c 실시간 latency + commercial TTS / F5-TTS / CosyVoice 2 비교
   - §3.3.7d Text-side style fine-tuning 권고 (Prompt vs LoRA, 한국어-영어 code-switch 가능 LLM, fine-tuning 작업, 데이터 요구량, corpus 출처)
   - §3.3.7e 종합 권장 아키텍처 (4-레이어 + fine-tuning 통합 다이어그램)
3. **산출물** (.research/)
   - `style-card.v1.schema.json` — JSON Schema draft 2020-12, 1.0.0
   - `style-card-builder.py` — transcript → card CLI (`--validate`)
   - `test-transcript.txt` + `test-card.json` — 14 utterance 한국어-영어 code-switch 합성 transcript로 end-to-end 검증 통과 (filler 분포 음/어/I mean/그/you know/아/like, korean_anchor_rate 0.714, default_per_utt 1.43)
4. **paper-search 스킬 추가 시도** — semantic_scholar·scopus IP 차단, eric만 동작하지만 토픽 미스매치 (교육연구 논문 다수, voice cloning 없음)
5. **history.md** 현재 세션 갱신

#### 변경/생성 파일
- 생성: `.research/2026-09-09_voice-cloning-style-verdict.md`, `.research/style-card.v1.schema.json`, `.research/style-card-builder.py`, `.research/test-transcript.txt`, `.research/test-card.json`
- 수정: `1. GE-AI_technical-report.md` (1133 → 1331 lines, +198), `history.md` (이 세션)

#### 결정 사항
(D32) 화자 동일성 보존은 **4개 독립 레이어**로 분해한다 (L1 timbre / L2 prosody / L3 lexis-syntax / L4 discourse-habit). 텍스트 LLM은 L3·L4 + L2-text를 담당. 우리 §3.3에서 L1·L2는 reference로만, L3·L4를 본격 다룸.

(D33) L3·L4 보존은 **system-prompt-conditioned(§3.3.1)보다 LoRA fine-tuning이 본질적으로 우월** — 스타일 일관성·L4 disfluency internalize·inference latency 동일(또는 더 빠름). 하이브리드 권장: 1차 system-prompt-conditioned로 D-day 작동 → 안정화 후 fine-tune 전환.

(D34) 한국어-영어 code-switching LLM 1순위 = **Qwen 3.6 14B** (Apache-2.0, 다국어 최상급) 또는 **EXAONE 3.x 7.8B** (LG AI Research, 한국어 1등). HyperClova X는 fine-tuning 불가로 제외. Solar는 CC-BY-NC로 상업 사용 불가.

(D35) TTS 우선순위: **CosyVoice 2 (instruction-based style control) > F5-TTS > commercial TTS** (latency 최소지만 L4·L2 정밀 통제 불가). commercial TTS는 L4 disfluency가 LLM 자연 텍스트로 처리될 때만 충분.

(D36) Fine-tuning 데이터 요구량: **300–1,000 utterance (≈30–60분 자연 발화)**로 1차 작동 가능. 자체 수집 (Class B 녹음, IRB 동의) + ELFA/VOICE/ACE 보조.

(D37) Per-speaker LoRA adapter 30–80MB × 6화자군 = ~0.5GB, 충분히 관리 가능. Catastrophic forgetting 방지를 위해 QLoRA + 1e-5 ~ 5e-5 LR + ELFA 1k utt replay buffer 권장.

(D38) Style Card v1 schema 확정 (JSON Schema 2020-12, 1.0.0). L4 explicit token notation v1 (`[FILLER:음] [PAUSE:300ms] [FALSE_START] [REPAIR]`) — fine-tune 채택 시 불필요해질 수 있으나 system-prompt-conditioned backup path용으로 보존.

(D39) Surveyed venues — 4-레이어별 Tier 1 (텍스트 LLM): ACL/EMNLP/NAACL/SIGDIAL/AAAI/ICLR/NeurIPS/TACL / Tier 2 (음향): Interspeech/ICASSP/IEEE TASLP/IEEE SLT/SSW/Speech Communication/CSL/DiSS / Tier 3 (멀티모달): ACM MM/LREC/ACL SRW. 출판사 접근성: aclanthology.org + isca-archive.org 무료, IEEE Xplore paywall, arXiv preprint 1차.

#### 다음 우선순위 (D-4 KST 종료 시점, D-day 다음 주 월요일 = D-5)
1. **#1** voice-cloning doc §9 신설 + §3.1 표 L2/L3/L4 3행 분리 (1h, 즉시 가능, 사용자 시작 대기)
2. **#3** L4 explicit token notation + §7.1 시스템 프롬프트 예시 (1h, 즉시 가능)
3. **#6** 0903 DDR_3D_GE.md cross-reference (0.5h, 즉시 가능)
4. **#2** Style Card schema 정의서 작성 (3-5h, M) — **이미 완료**
5. 사용자 처리: 템플릿 발송 결과 확인, IRB 회신 확인, 다운로드한 6개국 corpus
6. 저자 처리: CosyVoice 2 셋업, MRPL2 reference 추출, cascade 통합, Step C 검증
7. 보류: 한국어-영어 code-switching 정밀 검색 (Scopus API 정상화 또는 대학 VPN 후), 화자 transcript 기반 Style Card 값 채우기
8. **Fine-tuning PoC** (신규): Class B 1주차 시작 후 transcript 30분+ 수집 → Qwen 3.6 7B LoRA r=16 fine-tune → 6화자군 × LoRA adapter swap 검증

#### 메모/리스크
- 429 rate-limit이 Semantic Scholar / Scopus / DuckDuckGo 모두에 적용 (private API key 있어도 IP 차단). 후속 정밀 검색은 대학 VPN 또는 다른 IP에서 재시도 필요.
- §3.3 보강은 결론적. D-5까지 1주차 작동에 필요한 1차 system-prompt-conditioned 버전은 style card + few-shot으로 가능. fine-tune는 2주차 안정화 후 진행.
- Fine-tuning 시 human_reviewed 플래그를 true로 두려면 전문가 코딩 1 round 필요 (시간 추가). 1차 작동은 false로 진행하고 안정화 후 human-reviewed로 격상.

### 2026-09-09 (Wed, 22:42 KST) — 최종 Model 1–3 운영안 및 문서 정리

#### 확정 운영안

| 모델 | 기간 | 구성 |
|---|---:|---|
| **Model 1** | **1–2주** | Qwen 3.6 system-prompt-conditioned text generation + Style Card/RAG + CosyVoice 2 reference-audio TTS |
| **Model 2** | **3–4주** | Qwen 3.6 system-prompt-conditioned text generation + per-speaker CosyVoice 2 TTS LoRA |
| **Model 3** | **5–8주** | Qwen 3.6 QLoRA + per-speaker TTS LoRA + VOICE/ACE/ELFA pragmatic-function data |
| **비교 실험** | **9–10주** | Model 3의 Qwen 3.6과 Qwen 3.8을 동일 조건에서 비교 |

1–2주차에는 음성 구축만 진행하고 3D avatar·camera·lip-sync는 3주차 이후로 미룬다. Intel Arc 노트북은 client·데이터 준비만 맡고 inference와 fine-tuning은 필요한 시간에만 cloud GPU를 사용한다. 별도 backup API와 24/7 GPU 임대는 운영안에서 제외한다.

#### 결정 사항

- D-day baseline은 **Qwen 3.6**이다.
- Qwen 3.8은 9–10주차 비교 대상이며, “thinking preservation” 우월성은 benchmark 전까지 주장하지 않는다.
- 현재 운영 경로에서는 Qwen 3.6을 사용하고, Qwen 3.8은 후속 비교 대상으로만 둔다. 다른 provider backup은 사용하지 않는다.
- 한국어식 filler 예시는 삭제하고, 화용 전략은 L1-agnostic ELF interaction pattern으로 기술한다.
- L5a는 QLoRA, L5b는 system prompt/RAG, L5c는 model capability와 interaction design을 통해 평가한다.

#### 비용 및 리스크

80명 × 주 5분 × 10주 = 약 66.7시간이다. 필요한 시간만 GPU를 임대하는 경우 약 **$67–100/학기**를 계획한다. 실제 가격은 provider·GPU·동시접속·serving 설정에 따라 검증해야 한다. Qwen 3.8의 성능 차이와 CosyVoice 2 latency도 동일 test set과 실제 cloud 환경에서 측정한다.

#### 문서 반영

- `1. GE-AI_technical-report.md`: 앞부분 SSOT를 Model 1–3 체계로 개편하고, 이전 단계 표기·backup path·구형 모델·한국어 filler 예시를 정리했다.
- `history.md`: 현재 운영안과 검증 리스크를 이 최종 기록으로 통합했다.

### 2026-09-10 (Thu) — DDR 3개 모델 비교를 전문가 인터뷰 설계로 전환

- `0903 DDR_3D_GE.md`를 기존 M1–M4 corpus-representation 비교에서 현재 **Model 1–3 누적 개발 경로**로 전면 정리했다.
- Model 1: Qwen 3.6 system prompt + Style Card/RAG + CosyVoice 2 reference audio.
- Model 2: Model 1 + per-speaker CosyVoice 2 TTS LoRA.
- Model 3: Model 2 + Qwen 3.6 QLoRA + ELF pragmatic-function data/RAG.
- 비교 방식은 학생 대상 실험이 아니라 **전문가 artifact rating + 반구조화 인터뷰**로 확정했다.
- 전문가 평가지표: ELF appropriateness, pragmatic strategy, interactional fit, intelligibility, voice consistency, prosody, stereotype risk, educational suitability, reproducibility, deployment feasibility.
- 1–2주차에는 3D avatar를 비교하지 않고 transcript/audio artifact를 사용하며, 3D shell은 3주차 이후 별도 확장한다.
- Model 1 system prompt v0.1과 Style Card template를 `.research/model1-expert-review/`에 동기화했다.
- Lee et al. (2025) ARAL은 개발 절차가 아니라 ELF communication strategy 평가 범주의 보조 참고자료로만 사용한다.
- 기존 §3.3.16.7에 남아 있던 A/B/B' L1–L5 표를 Model 1/2/3(1–2주/3–4주/5–8주) 표기로 교체했다.
- ICNALE SD의 participant metadata(CEFR 포함)를 연구 표집·분석에 사용하기로 확정했다. 이를 근거로 현재 SD를 가장 우선적인 Asian learner dialogue source로 유지한다.
- `2. corpus-application-notification-templates.md`에 ICNALE Spoken Dialogues용 Asian learner English access email 초안을 추가했다. transcript/audio/video 접근과 TTS·chatbot 출력은 별도 허가가 필요하다는 조건을 명시했다.

### 2026-09-11 — 음성 corpus와 대화 corpus 분리 판정

- Zenodo MRPL2, OpenSLR SLR101, TAMU L2-ARCTIC은 주로 read/pronunciation 자료로 분류했다. L2-ARCTIC suitcase subset은 spontaneous지만 약 26분으로 Model 3 fine-tuning source로는 부족하다.
- Model 3 text/ELF 자료는 실제 turn-based dialogue가 필요하다.
- 우선 조사 후보: ELFA(academic ELF, audio restricted), VOICE 3.0(자연 발생 ELF transcript), ACE(Asian interactive ELF), ICNALE Spoken Dialogues(controlled learner interaction), COREFL(audio+transcript).
- `1. GE-AI_technical-report.md` §9.10.0-A에 corpus 적합성 표와 접근 우선순위를 추가했다.

### 2026-09-11 — ICNALE Spoken Dialogues 영상·음성 활용 판정

- 약 40–45분 semi-structured interview는 Monologues보다 Model 3 대화·화용 자료로 적합하다고 판단했다.
- speaker diarization → 수동 timestamp 검수로 학생/인터뷰어를 분리한다. 겹침 발화는 TTS 학습에서 제외한다.
- 학생 audio + 정확한 학생 transcript는 Model 2/3 TTS LoRA 후보로, 전체 turn-labelled transcript는 Model 3 Qwen QLoRA/RAG 자료로 사용한다.
- 학생 약 30분은 음질이 양호하고 clean segment를 선별한다는 조건에서 TTS LoRA에 유망하나, 국가·English variety 전체를 대표하지 않는다.
- ENS=English Native Speakers, MYS=Malaysia, PAK=Pakistan으로 확인했다. 관련 상세 계획을 §9.10.0-B에 반영했다.

### 2026-09-11 — ICNALE 처리 분담과 synthetic persona 원칙

- diarization은 사용자가 전부 직접 할 필요 없이, 원본 video/mixed audio가 있으면 기술 측에서 extraction·speaker diarization·WhisperX timestamp·forced alignment·student-only export를 수행하고 사용자는 애매한 구간을 검수한다.
- 학생-only audio + matching transcript는 TTS LoRA용, 인터뷰어·학생 전체 turn-labelled transcript는 Model 3 text/ELF용으로 분리한다.
- 참가자별 일관된 chatbot identity는 필요하지만, 누락된 나이·영어 학습 이력 등을 실제 사실처럼 복원하지 않는다. observed/inferred/unknown을 구분하고 synthetic composite persona로만 설계한다.
- 관련 원칙을 `1. GE-AI_technical-report.md` §9.10.0-C에 반영했다.

### 2026-09-11 — ICNALE SD workbook inventory 반영

- `SD_0_All Utterances.xlsx`를 CSV와 JSON summary로 변환했다. `01_Participants` 기준 425명, 425개 고유 speaker code이며 task 반복은 중복 참가자가 아니다.
- region별: ENS 20; Expanding operational CHN 50, TWN 50, IDN 30, JPN 100, THA 40, KOR 20; Outer HKG 30, PHL 40, MYS 20, PAK 25. KOR 20도 현재 source pool에 포함한다.
- SD_0/1/2/3 전사 폴더의 역할과 `03_Transcript` 기반 Model 3 sampling 절차를 정리했다. `sample_files`는 열지 않고 보류했다.
- 현재 pilot은 CHN·JPN의 Introduction, Picture Q&A, Role-play Q&A에서 시작한다. 상세 내용은 기술보고서 §9.10.0-D/E에 반영했다.

### 2026-09-11 — ICNALE SD CEFR level 반영

- `01_Participants`의 CEFR metadata를 확인했다: learner 405명 중 A2_0 66, B1_1 89, B1_2 173, B2+ 77; ENS 20은 N/A.
- CEFR은 transcript에서 임의 추정하지 않고 participant metadata로 사용한다. Model 1에서는 응답 길이·어휘 조절, Model 3에서는 sampling stratification과 pragmatic 분석에 사용한다.
- `SD_cefr_summary.json`을 생성하고 기술보고서 §9.10.0-F에 반영했다.

### 2026-09-11 — Model 1 pilot 3개 source freeze 및 full audio 추출

- 국가별 원본 번호가 가장 낮은 3개를 선택: `ICNALE_SD_CHN_004`, `ICNALE_SD_IDN_001`, `ICNALE_SD_JPN_002`.
- 원본 보존, 16kHz mono PCM full mixed audio 추출, metadata/manifest 생성 완료.
- `model1_pilot/03_qc`와 `04_student_audio_pending`은 다음 diarization·alignment 단계용으로 남겼다.
- `sample_files`의 다른 파일은 열거나 처리하지 않았다.

### 2026-09-11 — Model 1 diarization 준비

- `ICNALE_SD_CHN_004`, `ICNALE_SD_IDN_001`, `ICNALE_SD_JPN_002`의 full stereo WAV를 확인하고 diarization 작업 구조를 만들었다.
- 순서: pyannote diarization → RTTM/segments CSV → Student/Interviewer role mapping → human review → overlap 제거 → student-only export.
- 재사용 스크립트: `scripts/diarize_model1.py`; review template: `model1_pilot/03_qc/diarization_review_template.csv`.
- 현재 환경에는 pyannote.audio와 Hugging Face token이 없어 자동 실행은 보류했다. token은 코드/history에 저장하지 않는다.

### 2026-09-12 — PowerShell diarization launcher 추가

- 긴 명령어 붙여넣기 오류를 방지하기 위해 `scripts/run_model1_ch04.ps1`을 추가했다.
- 사용자는 token을 설정한 같은 PowerShell에서 짧은 launcher 명령만 실행한다.
- launcher는 CHN pilot 입력과 output 경로를 내부에서 고정하며 HF_TOKEN을 파일에 저장하지 않는다.

### 2026-09-12 — Windows TorchCodec/FFmpeg 환경 수정

- diarization 실행 중 TorchCodec DLL 오류를 확인했다. 원인은 Windows shared FFmpeg dependency 부재였다.
- isolated `.venv-diarization`에 `av`와 shared FFmpeg 9.0.1을 준비하고, CHN stereo WAV의 `AudioDecoder` 로딩을 확인했다.
- `run_model1_ch04.ps1`이 shared FFmpeg bin을 실행 시 PATH에 추가하도록 수정했다. 현재 남은 실행 조건은 Hugging Face token/model access다.

### 2026-09-12 — Singapore controlled pronunciation resource 기록

- Singapore recording set은 CMU ARCTIC-derived controlled read-speech prompt를 사용하는 pronunciation/acoustic comparison 자료로 기록했다.
- 논문에서는 동일 prompt 기반의 pronunciation, intelligibility, ASR, phoneme/word alignment, prosody/acoustic 비교 용도로 명시한다.
- conversational style, ELF pragmatics, Model 3 dialogue 자료로 사용하지 않는다. 최종 corpus명·provider attribution·license·access date는 원자료 documentation으로 확인한다.

### 2026-09-12 — CHN speaker diarization 성공

- `ICNALE_SD_CHN_004_FULL_STEREO.wav`에 `pyannote/speaker-diarization-community-1` 실행 성공. RTTM과 segment CSV 생성.
- 583 segments: SPEAKER_00 214개/원시 731.1초, SPEAKER_01 369개/원시 1340.0초. 0.5초 미만 fragment 191개로 overlap·boundary 검수 필요.
- 모든 role은 아직 UNKNOWN이며, 영상·`03_Transcript` 대조 후 Student/Interviewer를 확정한다. IDN·JPN은 CHN 검수 후 같은 pipeline 적용.

### 2026-09-12 — CHN provisional role mapping·audio candidate 생성

- `03_Transcript`의 `[T]`/`[S]` 초반 turn과 diarization 결과를 대조해 `SPEAKER_00=Interviewer`, `SPEAKER_01=Student` provisional mapping을 만들었다.
- 겹침을 제외한 0.5초 이상 SPEAKER_01 구간을 masking 방식으로 이어 붙인 `ICNALE_SD_CHN_004_STUDENT_PROVISIONAL.wav`를 생성했다.
- 이는 source separation/최종 TTS reference가 아니며, 영상·transcript 수동 검수 후 확정한다.

### 2026-09-12 — 다음 세션 handoff: CHN diarization 검수 대기

**현재 확정 상태**

- Model 1 pilot source는 `ICNALE_SD_CHN_004`, `ICNALE_SD_IDN_001`, `ICNALE_SD_JPN_002`이다.
- canonical ID 규칙은 `ICNALE_SD_<region>_<original_id>`이다.
- CHN에 대해서만 pyannote diarization 실행을 완료했다.
- 산출물:
  - `voices/Asian_Learners_ICNALE/Spoken_dialogue/model1_pilot/05_diarization/ICNALE_SD_CHN_004/ICNALE_SD_CHN_004.rttm`
  - `voices/Asian_Learners_ICNALE/Spoken_dialogue/model1_pilot/05_diarization/ICNALE_SD_CHN_004/ICNALE_SD_CHN_004_segments.csv`
- CHN segment는 583개이며 `SPEAKER_00` 214개, `SPEAKER_01` 369개다. 0.5초 미만 fragment가 191개이므로 겹침·boundary fragment를 검수해야 한다.
- 초반 `03_Transcript`의 `[T]`/`[S]` 순서에 근거한 provisional mapping은 `SPEAKER_00=Interviewer`, `SPEAKER_01=Student`이다. 영상 전체 검수 전에는 확정하지 않는다.
- provisional student candidate:
  `voices/Asian_Learners_ICNALE/Spoken_dialogue/model1_pilot/04_student_audio_pending/ICNALE_SD_CHN_004/ICNALE_SD_CHN_004_STUDENT_PROVISIONAL.wav`
  이는 overlap을 제외한 masking 결과이며 최종 TTS reference가 아니다.

**다음 세션 실행 순서**

1. **ICNALE 추가 자료 다운로드부터 시작:** `https://onedrive.live.com/shared`에 접속해 허가된 ICNALE 파일을 확인·다운로드한다.
2. 다운로드한 파일의 source/license/participant metadata를 먼저 manifest에 기록한다.
3. **Singapore 자료 확인·다운로드:** Dropbox에 `seongyonglee77@gmail.com` 계정으로 접속해 필요한 소수 화자 subset만 다운로드한다. 비밀번호와 token은 history·코드·채팅에 기록하지 않는다.
4. Singapore subset 파일의 다운로드 완료·무결성·license 기록을 확인한 직후 Dropbox의 **자동 갱신을 해제/구독을 취소**한다. 취소 확인 화면이나 이메일만 보관하고, 필요한 연구 파일은 제한 저장소에 남긴다.
5. CHN video와 `ICNALE_SD_CHN_004_segments.provisional_roles.csv`를 대조해 `SPEAKER_00/01` role을 확정한다.
6. `03_qc/ICNALE_SD_CHN_004_role_map.provisional.csv`의 `final_review`와 role을 갱신한다.
7. 확인된 Student 구간과 matching transcript를 기준으로 최종 student-only WAV를 export한다.
8. CHN 결과가 맞으면 동일한 launcher/pipeline을 IDN_001과 JPN_002에 적용한다.
9. 세 화자의 최종 audio quality와 transcript alignment를 검수한 뒤 Model 1 CosyVoice 2 reference test로 이동한다.

**환경 재개 방법**

- 새 PowerShell마다 Hugging Face token을 다시 환경변수로 설정한다. token은 history·코드·채팅에 저장하지 않는다.
- `D:\agent_project\2609_CA-GELT_Choe\.venv-diarization`을 사용한다.
- `scripts/run_model1_ch04.ps1`은 CHN 전용 launcher이며, shared FFmpeg bin을 PATH에 추가한다.
- 새 세션에서는 먼저 `HF_TOKEN` 설정 여부를 확인하고, CHN role 검수가 끝나기 전에는 IDN/JPN을 실행하지 않는다.
- `sample_files`의 다른 자료는 계속 열거나 처리하지 않는다.

관련 상세 문서:

- `1. GE-AI_technical-report.md` §9.10.0-F–J
- `voices/Asian_Learners_ICNALE/Spoken_dialogue/model1_pilot/manifest.v0.1.json`
- `scripts/diarize_model1.py`
- `scripts/export_diarized_audio.py`
- `scripts/run_model1_ch04.ps1`

### 2026-09-12 — Singapore subset download policy

- Singapore 자료는 **controlled read speech with spoken-like register variation**으로 표기한다. 구어적 문체·발음·rhythm·prosody에는 활용하지만 turn-taking/pragmatics 자료로 사용하지 않는다.
- 전체 약 2TB를 다운로드하지 않고, consent/license·speaker metadata·음질·prompt coverage를 기준으로 소수 화자 subset만 선정한다.
- 논문에는 subset size, speaker/anonymized IDs, access date, selection criteria를 기록한다.

### 2026-09-12 — 초기 음성자료 3개 acquisition track 기록

- ICNALE SD: `https://onedrive.live.com/shared`의 허가된 SD media를 우선 사용하며 source ID·CEFR·transcript·license scope를 유지한다.
- Singapore: Dropbox에서 소수 화자 subset만 다운로드하며 controlled read speech with spoken-like register variation으로 사용한다.
- VOICE/Helsinki–ACDH: VOICE 3.0(`https://voice3.acdh.oeaw.ac.at/`)와 Helsinki CoRD(`https://varieng.helsinki.fi/CoRD/corpora/VOICE/index.html`)에서 audio availability와 research-use permission을 확인한다. 공개 transcript와 일부 event audio playback은 확인되지만 bulk audio download은 확인 전제로 두지 않는다.
- 세 source를 manifest에서 분리하고 `source_id`, version, media type, access route, license scope, download date, permitted use를 기록한다.

### 2026-09-12 — TalkBank 추가 조사 track 기록

- 내일 기존 3개 acquisition track과 함께 **TalkBank를 4번째 자료 조사 track**으로 확인한다: [TalkBank](https://talkbank.org/).
- TalkBank는 인간 의사소통, 특히 spoken communication 연구를 위한 저장소이며, 14개 연구 영역과 42개 이상의 언어 자료를 제공한다. 자료는 CHAT(JSON 호환) 형식으로 표준화되어 있고 CLAN·TalkBankDB·Batchalign을 통한 검색·분석이 가능하다.
- 본 프로젝트의 우선 확인 순서는 다음과 같다.
  1. **CABank** — 성인 간 대화 및 conversation analysis 자료. 자연 발생 turn-taking·sequence·repair 분석 후보로 우선 검토한다: <https://talkbank.org/ca/>.
  2. **ClassBank** — 교실에서 촬영·전사된 상호작용(과학·수학·의학·읽기 등). Class B 수업 맥락과 교실 상호작용 설계 참고자료로 검토한다: <https://talkbank.org/class/>.
  3. **BilingBank / SLABank** — 다언어성 및 제2언어 습득 자료. ELF/learner interaction과의 직접 적합성, 영어 variety·participant metadata·audio/video 존재 여부를 확인한다: <https://talkbank.org/biling/> / <https://talkbank.org/slabank/>.
- TalkBank 자료는 bank/corpus별 접근 조건을 분리해 기록한다. 웹 설명은 공개지만 실제 transcript/media는 등록 필요, 연구자 승인, 또는 controlled access일 수 있으므로 다운로드·TTS·챗봇 출력·fine-tuning을 자동으로 허용한다고 가정하지 않는다: <https://talkbank.org/0share/access.html>.
- 내일 확인할 공통 필드: `bank/corpus`, corpus version, language/variety, participant metadata, transcript format/CHAT coding, audio/video availability, access level, license/ground rules, permitted use, citation, download route/date, Model 1/2/3 적합성.
- 현재 판정: TalkBank는 **Model 3 대화·화용 및 교실 상호작용 자료 후보**이지, 공개 개인 음성을 identity clone source로 쓰는 자료가 아니다. 실제 사용 전에는 consent·비식별화·2차 사용·TTS/LLM 학습 허용 범위를 corpus별로 확인한다.

**다음 세션의 자료 확인 묶음 (기존 3종 + TalkBank)**

1. ICNALE Spoken Dialogues — 허가된 OneDrive 자료와 metadata/license 확인.
2. Singapore controlled pronunciation set — 필요한 소수 subset과 consent/license 확인.
3. VOICE 3.0 / Helsinki CoRD — transcript·event audio·research-use permission 확인.
4. TalkBank — CABank → ClassBank → BilingBank/SLABank 순서로 corpus index, access level, media 및 Model 3 적합성 확인.

### 2026-09-13 — Model 1 CHN 정제 완료 및 다음 세션 handoff

- Model 1의 전체 진행 구조는 `docs/1. GE-AI_technical-report.md` §0.0–§0.0.1과 §9.10.0-G–J에 기록되어 있다. 핵심 경로는 `STT → Qwen 3.6 system prompt + Style Card/RAG → CosyVoice 2 reference-audio TTS → 웹 audio playback`이며, 3D avatar와 TTS LoRA는 이번 baseline 범위에 포함하지 않는다.
- CHN_004의 역할 매핑과 583개 segment 검수를 확정했다: `SPEAKER_00 → Interviewer`, `SPEAKER_01 → Student`; segment status는 모두 `VIDEO_REVIEWED`, role map은 `high/CONFIRMED`다.
- CHN_004 학생 음성 검수에서 인터뷰어 음성 40개 구간과 32:30–38:27 일본어 구간을 제외했다. 다음 clean 산출물을 생성했다.
  - `ICNALE_SD_CHN_004_SPEAKER_01_CLEAN_TIMELINE.wav` — 원본 시간축 보존 검수용
  - `ICNALE_SD_CHN_004_STUDENT_CLEAN.wav` — TTS/reference 후보
  - `ICNALE_SD_CHN_004_student_audio_exclusions.csv` — 제외 구간 audit log
- IDN_001·JPN_002는 full stereo WAV와 metadata까지 준비되어 있으나 role mapping 및 student-only export는 아직 미완료다. 긴 PowerShell 명령어 붙여넣기 오류를 방지하기 위해 `scripts/run_model1_remaining.ps1`을 추가했으며, 다음 세션에는 `.\scripts\run_model1_remaining.ps1 -SourceId IDN_001`과 `-SourceId JPN_002`를 각각 한 줄로 실행한다.

**다음 세션으로 이월한 자료 작업**

- 오늘 예정했던 voice 자료 다운로드·접근권 확인은 실행하지 않았으며 다음 세션으로 이월한다.
- 우선순위:
  1. ICNALE Spoken Dialogues 허가 자료 및 transcript/license metadata 확인.
  2. Singapore controlled pronunciation subset 다운로드 및 license/consent 기록.
  3. VOICE 3.0/Helsinki CoRD의 audio availability와 research-use permission 확인.
  4. 필요 시 TalkBank의 CABank → ClassBank → BilingBank/SLABank 접근 조건과 media availability 조사.
- 외부 자료는 다운로드 전에 permitted use, TTS/voice cloning 허용 범위, citation, access date를 기록한다. token·비밀번호·개인정보는 history나 코드에 저장하지 않는다.

### 2026-09-13 — Model과 화자 AI 분리 구조 및 Ollama 정책 확정

- 홈페이지는 Model 1·Model 2·Model 3을 별도 연구 모델로 제공하되, 각 Model 안에서 여러 화자 AI를 선택하는 단일 앱 구조로 확정했다.
- 화자 AI는 별도 챗봇이 아니라 `persona_id`·`voice_id`·Style Card·승인된 reference audio·consent scope를 가진 runtime 설정이다.
- 음성 선택만으로 챗봇을 복제하지 않는다. 필요한 경우 memory namespace는 `(participant_id, model_id, persona_id)`로 분리한다.
- Ollama는 Model 1·2·3의 필수 구성요소가 아니다. 기본 실행은 hosted/cloud Qwen endpoint로 하며, Ollama는 로컬 Qwen smoke test가 필요할 때만 선택적으로 설치한다.
- Model 1은 hosted Qwen + reference-audio TTS, Model 2는 hosted Qwen + speaker TTS LoRA, Model 3은 cloud QLoRA serving + speaker TTS LoRA 경로를 기본으로 한다.
- 위 구조와 Ollama 정책을 `docs/1. GE-AI_technical-report.md` §0.0.0–§0.0.0.1에 기록했다.

### 2026-09-13 — Model 1 CHN_004 baseline reference 확정

- 첫 Model 1 technical baseline 화자는 `ICNALE_SD_CHN_004` 학생 화자로 확정했다.
- canonical base는 `ICNALE_SD_CHN_004_STUDENT_CLEAN.wav`이며, 약 19분의 clean student-only audio에서 20–60초 reference clip을 별도 추출한다.
- `SPEAKER_01_CLEAN_TIMELINE.wav`는 QC/alignment용, `STUDENT_PROVISIONAL.wav`와 이전 concatenated 결과는 canonical reference에서 제외한다.
- ICNALE의 TTS·voice cloning·chatbot 출력 허가가 확인되기 전에는 CHN_004를 공개 voice clone이나 연구 산출물로 사용하지 않고 내부 pipeline 검증에만 사용한다.
- 이 파일 역할과 권리 gate를 `docs/1. GE-AI_technical-report.md`의 Model 1 baseline 화자 절에 기록했다.

### 2026-09-13 — Qwen hosted provider 후보 구체화

- Model 1의 첫 hosted Qwen provider 후보를 Alibaba Cloud Model Studio로 정리했다. Ollama나 로컬 GPU 설치는 필요하지 않다.
- OpenAI-compatible Singapore base URL 형식은 `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`이며, API key와 endpoint는 같은 region을 사용해야 한다.
- 실제 API model ID는 계열명 `Qwen 3.6`이 아니라 provider가 제공하는 정확한 ID를 사용한다. 첫 연결 후보는 `qwen3.6-flash`, 품질 비교 후보는 `qwen3.6-plus`다.
- 공식 문서: <https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope>.

### 2026-09-13 — 음성 provenance 문서와 Model Studio fine-tuning 경계 기록

- 실제 사용 음성의 source, 원본·파생 파일, transcript, license, consent, TTS/chatbot/public 사용 범위, 처리 이력을 별도 문서 `voices/voice-sources.md`에서 관리하기로 했다.
- `docs/1. GE-AI_technical-report.md`에는 `voices/voice-sources.md`를 음성 provenance 운영 SSOT로 연결하고, CHN_004 baseline과 파일별 역할을 유지했다.
- Alibaba Cloud Model Studio는 inference API만이 아니라 지원 model·region에 대해 별도 fine-tuning job과 custom model deployment를 제공한다. 그러나 chat completion 호출 자체가 fine-tuning을 수행하는 것은 아니다.
- Model 1은 hosted inference만 사용하고 fine-tuning하지 않는다. Model 3 Qwen fine-tuning은 정확한 model ID·region의 training method 지원을 확인한 뒤 Model Studio managed training 또는 외부 cloud GPU QLoRA 중 선택한다.
- 현재 확인 기준 `qwen3.6-flash`는 Singapore hosted inference는 가능하지만 Singapore fine-tuning은 지원되지 않는다. 따라서 Model 3에서 Qwen fine-tuning이 필요하면 지원 region/model을 별도로 선택하거나 외부 cloud GPU QLoRA를 사용한다.
- Qwen fine-tuning에는 text JSONL을 업로드하며, CHN_004 음성 reference와 CosyVoice TTS 학습은 별도 처리한다. source의 third-party cloud processing·LLM training 허가 없는 자료는 업로드하지 않는다.

### 2026-09-13 — Alibaba Model Studio를 Qwen text layer 통합 후보로 승격

- Qwen은 transcript·Style Card·persona context를 받아 text response를 생성하고, 음성 생성은 Deepgram STT 및 CosyVoice 2 TTS와 분리한다.
- Alibaba Model Studio는 inference API뿐 아니라 지원되는 model·region에 대해 text fine-tuning job과 custom model deployment를 제공하므로, Model 3 Qwen text-side managed training의 1차 후보로 승격했다.
- Model 1은 base Qwen hosted inference, Model 2는 Qwen text 경로 유지 + TTS LoRA, Model 3은 Model Studio managed training 또는 외부 QLoRA로 분기한다.
- Model Studio의 `efficient_sft`와 연구 설계상의 `QLoRA`는 자동으로 동일하다고 기록하지 않는다. 실제 model·region·training method·deployment plan을 확인해 명시한다.
- Voice Agent는 primary 경로에서 제외한다. Deepgram → Qwen text → CosyVoice 2 분리 cascade를 유지한다.

### 2026-09-13 — CHN_004 사용 허가 확인 및 SFT 준비 조건 반영

- 사용자가 CHN_004 음성의 사용 허가를 확인했으므로 Model 1 baseline 진행을 승인 상태로 갱신했다.
- `voices/voice-sources.md`의 CHN_004 상태를 `APPROVED_TTS`로 갱신하고, 승인 문서·이메일 경로와 Qwen text SFT/cloud processing 범위는 별도로 기록하도록 했다.
- `SFT`를 `Supervised Fine-Tuning`으로 명시하고, Alibaba Model Studio의 ChatML JSONL assistant response 학습 방식과 Model 3 적용 후보를 기술보고서에 반영했다.
- 사용자에게 필요한 Qwen 정보는 model file이 아니라 Model Studio의 API key, workspace/region, API host, 정확한 base model ID, training method 지원 여부, billing/permission 상태다.

### 2026-09-13 — Model Studio workspace credential 확인

- 사용자가 Model Studio에서 `apiKey`, `apiHost`, `openAiCompatible`, `dashScope`, `workspaceName`, `workspaceId` 정보를 발급받았다.
- `ws-...ap-southeast-1.maas.aliyuncs.com`처럼 provider host에 region이 포함되므로 별도 region 선택을 다시 요구하지 않는다.
- OpenAI SDK의 `base_url`은 반환된 `openAiCompatible` 값을 우선 사용하고, `apiKey`는 문서·history·source에 저장하지 않는다.

### 2026-09-13 — Model 1 우선 개발과 annotation 선행 준비 확정

- 개발 순서를 Model 1 cascade 완성 → Model 2 확장 → Model 3 확장으로 확정했다. Model 2·3은 Model 1의 cascade와 voice/persona 선택 구조를 재사용한다.
- 동일 voice source는 Model 1·2·3에서 재사용할 수 있으나, train/dev/test 발화는 분리하고 source provenance·annotation version을 공유한다.
- CA·화용·대화 기능 annotation과 acoustic/prosodic annotation은 Model 2·3 시작 때까지 미루지 않고 Model 1 개발과 병행해 master annotation으로 준비한다.
- Model 1은 최소 annotation(speaker/turn/timecode, clean·overlap/exclusion, matching transcript, pause·WPM)으로 먼저 작동시키고, 전체 CA annotation은 Model 1 개발 중 확장한다.
- Model 2 진입 전 acoustic annotation을 확정하고, Model 3 진입 전 CA·화용·대화 기능 annotation을 승인된 ChatML text dataset과 Qwen SFT(Supervised Fine-Tuning)/RAG 입력으로 변환한다.
- 현재 설계·API·CHN_004 clean base는 개발 착수 가능하지만, 앱/service/test code, CosyVoice 실행 연결, reference clip·matching transcript는 아직 구현·생성해야 한다. 현재 coding model(Luna-high)로 착수하며 Terra 5.5/5.6 전환은 필요조건으로 두지 않는다.

### 2026-09-13 — Model 1 Phase 1 core 구현 및 검증

- `services/model1/`에 provider-isolated Deepgram STT, Alibaba Qwen OpenAI-compatible chat, Beijing CosyVoice 2 TTS adapter, `Model1Cascade` orchestration을 추가했다.
- `scripts/prepare_chn004_reference.py`와 fake/fixture 기반 reference 테스트를 추가했다. WAV frame-preserving extraction, candidate listing, explicit timed-transcript gate, `source_paths` manifest, no-overwrite를 포함한다.
- 현재 untimed `ICNALE_SD_CHN_004_transcript.csv`에서 matching transcript를 추정하지 않도록 했다. `REFERENCE_01.wav/.txt/.manifest.json` 생성은 timed transcript 준비 후 수행한다.
- 검증 명령: `python -m pytest -q tests/test_model1_cascade.py tests/test_chn004_reference.py` → **13 passed**.
- 검증 명령: `python -m py_compile services/model1/__init__.py services/model1/config.py services/model1/cascade.py services/model1/tts.py scripts/prepare_chn004_reference.py` → 성공.
- live API 호출·voice enrollment·browser/audio playback은 아직 실행하지 않았으며, 다음 phase의 검증 대상이다.

### 2026-09-13 — Model 1 live provider smoke 결과

- `.env.local`을 읽어 CHN_004 clean audio 10초를 Deepgram에 전송했고 STT 인증·요청은 성공했다.
- 같은 transcript를 Singapore Model Studio Qwen endpoint에 전송한 결과 HTTP 401이 반환됐다. Qwen key·endpoint·workspace·region 일치 여부를 해결하기 전에는 Qwen 성공으로 기록하지 않는다.
- Qwen 401로 인해 이번 실행에서는 Qwen 이후 CosyVoice 호출을 진행하지 않았다.

### 2026-09-13 — CHN_004 reference audio provisional extraction

- `scripts/prepare_chn004_reference.py`에 `--audio-only`를 추가해 timed transcript가 없을 때도 false transcript 없이 WAV와 pending manifest만 생성하도록 했다.
- diarization/제외 구간 기준으로 algorithmically safe한 759.338–779.338초 구간을 선택해 다음을 생성했다.
  - `voices/Asian_Learners_ICNALE/Spoken_dialogue/model1_pilot/04_student_audio_pending/ICNALE_SD_CHN_004/reference/ICNALE_SD_CHN_004_REFERENCE_01.wav`
  - `.../ICNALE_SD_CHN_004_REFERENCE_01.manifest.json`
- matching `.txt`는 current untimed transcript로 추정하지 않았으며, human listening review는 pending으로 남겼다.
- 검증 명령: `python -m pytest -q tests/test_model1_cascade.py tests/test_chn004_reference.py` → **13 passed**.

### 2026-09-13 — Beijing Qwen 접근 상태 확인

- Beijing workspace의 원본 key와 Beijing `openAiCompatible` endpoint로 `qwen3.6-27b` 호출을 시도했다.
- 결과는 HTTP 403 `AccessDenied.Unpurchased`였다. 이는 key/endpoint가 도달했지만 해당 workspace에서 model service 구매·활성화 또는 model authorization이 완료되지 않았다는 의미다.
- Model 1의 Beijing Qwen live test는 Qwen3.6-27B를 해당 workspace에서 활성화한 뒤 재시도한다. Deepgram 설정은 별도이며 이번 test에서 성공 상태를 유지했다.

### 2026-09-13 — Qwen Singapore·CosyVoice Beijing 분리 확정

- 앞서 제안한 “Qwen과 CosyVoice를 Beijing으로 통일”은 기본 결정으로 사용하지 않는다.
- 현재 운영 구성은 Singapore Qwen(`DASHSCOPE_API_KEY`, `QWEN_BASE_URL`)과 Beijing CosyVoice 2(`DASHSCOPE_API_KEY_COSYVOICE`, `COSYVOICE_WS_URL`, `COSYVOICE_CLONE_URL`)를 분리한다.
- Beijing의 `AccessDenied.Unpurchased`는 Beijing Qwen을 사용할 때의 별도 model activation 문제이며, 현재 Model 1의 Singapore Qwen 설정을 Beijing으로 바꾸는 근거가 아니다.
- 이 region 분리와 key 유지 원칙을 technical report에 명시했다.

### 2026-09-13 — Beijing workspace authorization 확인 및 최종 region 통일

- 사용자가 Beijing Default Business Space의 model authorization 화면을 확인했다.
- `qwen3.6-27b`에 대해 Model Invocation, Model Training, Model Deployment가 모두 `Authorized`로 표시됨을 확인했다.
- 이에 따라 Model 1 runtime은 Beijing Model Studio로 통일한다: Beijing Qwen3.6-27B text + Beijing CosyVoice 2 TTS.
- `.env.local`의 `DASHSCOPE_API_KEY`, `QWEN_BASE_URL`, Qwen model을 Beijing 기준으로 정비하고, CosyVoice Beijing 설정과 같은 원본 key를 별도 변수로 유지했다.
- 이전 Singapore Qwen 401 경로는 fallback 기록으로 남기고 현재 runtime에서 제외한다. 남은 확인은 Model Market의 model service activation/billing이며, 이것이 해결되면 Beijing Qwen live test를 재실행한다.

### 2026-09-13 — Singapore primary 경로로 최종 전환

- Beijing 경로는 Qwen 권한이 `Authorized`여도 중국 본토 identity verification과 model service eligibility가 추가로 요구되므로 primary에서 제외했다.
- 개인정보 보호와 즉시 개발 가능성을 우선해 Singapore Qwen3.6-27B + Singapore CosyVoice v3-plus를 Model 1 primary로 확정했다.
- 정확한 CosyVoice 2는 Beijing 신원 인증을 선택하는 후속 경로로 남긴다. Singapore voice cloning에는 CosyVoice v3-plus를 사용한다.
- `.env.local`의 endpoint/model 설정을 Singapore로 전환했다. Singapore 원본 API key 두 개는 사용자가 발급·확인한 뒤 각각 `DASHSCOPE_API_KEY`와 `DASHSCOPE_API_KEY_COSYVOICE`에 입력해야 한다.

### 2026-09-13 — Singapore Model 1 live smoke 성공

- Singapore Qwen3.6-27B와 Singapore CosyVoice v3-plus로 `.env.local` endpoint/model 설정을 재검증했다.
- Qwen 단문 호출 성공: response 31자, latency 5.890초.
- CHN_004 clean audio 10초 → Deepgram STT → Singapore Qwen3.6-27B 호출 성공.
- 관찰값: transcript 84자, Deepgram 1.172초, Qwen response 209자, Qwen 13.750초. 단일 smoke test 값이며 평균 성능으로 해석하지 않는다.
- CosyVoice v3-plus live voice enrollment/TTS는 `voice_id`와 HTTPS reference URL 준비 후 실행한다.

### 2026-09-14 — CosyVoice 2 경로 제거

- `CosyVoice 2`는 Singapore에서 CHN_004 voice cloning에 사용할 수 없어 Beijing identity verification이 필요한 별도 경로였으며, 품질이 v3-plus보다 우수하다는 근거는 확보되지 않았다.
- 사용자의 개인정보 보호 결정을 반영해 Beijing 인증·CosyVoice 2를 backup/primary 어느 쪽으로도 유지하지 않는다.
- 현재 Model 1 canonical TTS는 Singapore `cosyvoice-v3-plus`로 고정한다. 기술보고서와 `voices/voice-sources.md`의 active plan을 이에 맞춰 정정했다.

### 2026-09-13 — CHN_004 persona approval and registry verification

- 사용자가 CHN_004 profile의 research, STT/transcription, TTS reference, chatbot output, public demo, LLM text training, third-party cloud processing 전체 사용을 승인했다.
- `voices/personas/icnale_chn_004_student.json`의 `rights_status`를 `approved`로 갱신하고 permitted uses와 project owner 보관 승인 이메일 기준을 기록했다.
- `voices/personas/registry.json`은 `persona_id → profile JSON` 연결 manifest이며, `PersonaRegistry`가 profile의 voice_id·prompt_context·source_grounded/fictionalized/behavior를 검증해 `run_persona()`에 전달한다.
- 신규 voice source도 동일하게 profile 작성 → source_grounded/fictionalized/behavior 분리 → rights 승인 → registry 연결 → fake resolution/prompt test 순서를 따른다.
- 전체 검증: `python -m pytest -q` → **17 passed**; persona/cascade/reference/환경설정 포함. `python -m py_compile` 대상 파일 성공.

### 2026-09-14 — Model 1 executable execution layer

- Singapore CosyVoice v3-plus voice enrollment adapter와 persona-driven one-turn runner를 추가했다.
- runner는 `.env.local`, `voices/personas/registry.json`, approved persona profile을 읽고 `Model1Cascade.run_persona()`를 호출한다.
- 출력 audio와 response sidecar를 저장하며 sidecar에는 transcript/response/API key/raw audio를 저장하지 않고 길이·timestamp·latency만 기록한다.
- 전체 검증: `python -m pytest -q` → **21 passed**; `py_compile` 성공.
- live CosyVoice enrollment은 HTTPS reference URL과 provider가 반환하는 실제 `voice_id` 준비 후 실행한다.

### 2026-09-14 — CHN_004 timed reference transcript 생성

- `REFERENCE_01.wav`를 Deepgram `nova-3`에 전송해 timed transcription을 생성했다.
- `REFERENCE_01_timed_transcript.csv`에 6개 utterance의 start/end/text를 기록하고, matching `.txt` sidecar와 manifest의 `source_paths.timed_transcript`를 갱신했다.
- 이 transcript는 provider-derived 결과이므로 human review 후 canonical matching transcript로 확정한다. 원본 ICNALE transcript와 diarization 파일은 변경하지 않았다.

### 2026-09-14 — Singapore CosyVoice enrollment 및 Model 1 cascade 성공

- Alibaba OSS Singapore private object의 temporary signed URL을 사용해 CHN_004 reference WAV를 Singapore `cosyvoice-v3-plus` voice enrollment에 전달했다.
- 실제 voice ID를 발급받아 `voices/personas/icnale_chn_004_student.json`에 연결했다. signed URL은 enrollment에만 사용하며 profile에는 URL을 저장하지 않는다.
- `dashscope` SDK를 설치하고 `scripts/run_model1_turn.py`로 CHN_004 reference audio → Deepgram → Qwen3.6-27B → CosyVoice v3-plus → MP3 output 전체 cascade를 성공시켰다.
- 산출물: `artifacts/model1/chn004_cli_response.mp3`, redacted sidecar `artifacts/model1/chn004_cli_response.mp3.json`.
- 관찰값: STT 1.375초, Qwen 33.984초, TTS 9.516초, first audio 44.875초. 단일 smoke 값이며 평균 성능으로 해석하지 않는다.
- `research/test-transcript.txt`의 14개 발화에 대해 Qwen → CosyVoice quality sweep도 14/14 성공했다. 일시적 provider error 1건은 재시도 후 성공했으며, 평균 Qwen 15.953초·TTS 8.385초와 redacted summary/MP3 outputs를 `artifacts/model1/quality_sweep/`에 기록했다.

### 2026-09-14 — Model 1 latency 개선

- Qwen non-streaming payload에 `enable_thinking=false`, `max_tokens=256`을 적용해 짧은 conversational reply의 불필요한 reasoning 대기를 제거했다.
- 저지연 전체 cascade 성공: STT 1.125초, Qwen 1.812초, TTS 8.344초, first audio 11.281초.
- 동일한 14개 test utterance를 재실행해 14/14 성공했다. 평균 Qwen 1.683초, 평균 TTS 5.541초.
- 변경된 Qwen 설정은 `.env.example`, `.env.local`, `Model1Config`, Qwen adapter에 반영했으며 전체 테스트는 계속 21 passed 상태다.

### 2026-09-14 — Model 1 local student communication loop

- `scripts/run_model1_mic.py`를 추가해 local microphone recording → temporary WAV → 기존 `run_model1_turn.py` → MP3 output/playback 경로를 연결했다.
- `sounddevice`를 설치하고 input-capable audio device를 확인했다. 실제 녹음은 사용자가 명시적으로 실행할 때만 수행한다.
- microphone runner fake tests를 포함해 전체 테스트가 **25 passed**이고 `py_compile`도 성공했다.

### 2026-09-14 — Model 1 표준화 실행 경계

- Model 1 실행 구조를 `services/model1` provider/cascade core → `scripts` reproducible CLI/microphone runners → `apps` browser/websocket client로 고정했다.
- 웹 UI는 provider를 직접 호출하거나 두 번째 cascade를 만들지 않고 동일한 `services/model1` service boundary를 사용한다.
- 기존 batch runner는 진단·fallback으로 유지하고, 학생 대화의 primary 경로는 streaming STT → streaming Qwen → streaming TTS → incremental playback으로 전환한다.

### 2026-09-14 — Model 1 streaming core 구현

- `services/model1/realtime.py`에 Qwen SSE streaming, sentence chunking, CosyVoice WebSocket/`streaming_call` adapter를 추가했다.
- provider SDK는 lazy import하고 fake transport/callback 테스트 경계를 유지했다.
- 검증: 전체 테스트 **30 passed**, realtime/microphone/core 구문 검증 성공.
- 이 단계는 streaming service core이며 browser UI는 다음 adapter layer에서 동일 service boundary를 호출한다.

### 2026-09-14 — Model 1 browser WebSocket MVP 및 live session 연결

- `apps/model1_web/server.py`에 framework-light WebSocket protocol과 같은 포트의 static browser hosting을 연결했다.
- `apps/model1_web/static/app.js`는 microphone input을 16 kHz mono PCM으로 변환해 WebSocket으로 전송한다. provider endpoint/key는 browser에 노출하지 않는다.
- `DeepgramStreamingClient`와 `LiveModel1Session`을 `services/model1/realtime.py`에 추가해 configured server의 audio input을 Deepgram WebSocket으로 전달하고, stop 시 final transcript를 Qwen SSE와 CosyVoice streaming으로 처리한다.
- config가 없으면 server는 unsupported-audio 상태를 명시하고, `.env.local`이 있으면 `audio_input_supported=true` session을 만든다.
- 정적 hosting smoke: index/app.js HTTP 200 확인. 전체 검증: **39 passed**, `py_compile` 성공.
- 현재 경계: browser live provider end-to-end와 장시간 duplex/barging-in은 아직 별도 검증 대상이며, server session은 첫 버전에서 stop 후 response를 시작한다.

### 2026-09-14 — Browser trial latency·출력 길이·MP3 chunk 재생 수정

- 첫 browser trial에서 stop 이후 15초 이상 대기와 과도하게 긴 Qwen response를 확인했다. 원인은 realtime session이 full system/persona policy를 사용하지 않았고 Qwen output bound가 256 tokens였던 점이다.
- Stop 클릭 시 browser microphone capture를 즉시 중단하고, 서버에는 별도로 turn finalization을 요청하도록 수정했다. 따라서 응답 생성 시간 동안 추가 녹음이 계속되지 않는다.
- realtime session에 canonical Model 1 system policy/persona context와 `two short sentences / 48 words` constraint를 연결하고 `.env.local`의 `QWEN_MAX_TOKENS`를 96으로 낮췄다.
- CosyVoice callback의 MP3 frame chunks를 browser `decodeAudioData`에 개별 전달하던 방식에서 MediaSource `audio/mpeg` append queue로 변경했다. 이로써 chunk 단위 decode failure와 staccato/noise 문제를 피한다.
- live short smoke 관찰: Qwen streaming 3.031초, CosyVoice first audio 2.485초, TTS total 3.344초. 단문 단일 관찰값이며 microphone 전체 latency 평균은 아니다.
- 회귀 검증: **39 passed**, browser JavaScript `node --check` 성공.

### 2026-09-14 — Stop 처리·응답 길이·실시간 event delivery 보강

- Stop 클릭 즉시 microphone capture를 중단하고 elapsed timer/Stop control을 정리했다. 서버의 Deepgram finalize와 응답 생성은 별도 processing으로 표시한다.
- `LiveModel1Session.stream_stop()`과 protocol 지원을 추가해 Qwen text delta와 CosyVoice audio event를 full response 완료 전 WebSocket으로 전달한다.
- realtime prompt를 32 words/two sentences, no generic AI self-description/encyclopedia explanation으로 강화하고 browser text delta를 inline response로 표시한다.
- MP3 frame chunks는 browser MediaSource queue로 처리하고 fallback stop 결과는 하나의 audio event로 합쳐 chunk-boundary click 가능성을 줄였다.

### 2026-09-14 — 초기 latency 목표값 정정

- 기술보고서에 있던 `500–1200ms` cascade 및 `0.8–3초` 음성 입력 수치는 현재 provider/model/region 조합의 실측값이 아니라 초기 architecture target이었다.
- 실제 Singapore hosted Model 1에서는 Deepgram end-of-turn, Qwen TTFT, CosyVoice first audio, browser buffering이 누적되므로 1–2초 응답을 달성했다고 주장할 수 없다.
- 현재 Model 1의 acceptance metric은 `user_turn_end → first browser audio` 실측이며, 5초 이하의 일관된 대화가 필수인 production 경로는 integrated voice-agent 또는 lower-latency provider path를 별도 benchmark해야 한다.
- 이 차이를 숨기지 않고 technical report의 latency 표와 기록에 명시했다. 초기 목표값을 실제 보장값처럼 해석하지 않는다.

### 2026-09-14 — DDR와 Deepgram Voice Agent 경로 분리

- DDR이 어려워지는 것이 아니라, Model 1–3 개발 비교와 학생-facing low-latency 운영 경로를 같은 실험으로 섞으면 연구 해석이 어려워진다는 결론을 정리했다.
- DDR Study 2는 현재 Singapore cascade를 통제된 개발 baseline으로 유지한다: Model 1 cascade, Model 2 TTS LoRA, Model 3 Qwen SFT/QLoRA + delivery/profile control.
- Deepgram Voice Agent/Flux는 Model 1–3 중 하나가 아니라 별도 deployment benchmark 및 Study 1 승인 운영 도구 후보로 둔다. provider/turn detection/orchestration 차이 때문에 DDR cumulative model과 직접 비교하지 않는다.
- `docs/0914 DDR_3D_GE.md`에 두 경로의 평가 지표, latency acceptance gate, 단계별 산출물을 추가했다.

### 2026-09-14 — 교실 Voice Agent 전환 및 DDR cascade 일시 중단

- 교실 적용 연구는 Deepgram Voice Agent 또는 ElevenLabs Voice Agent 통합본을 사용해 실제 학생 interaction 경험을 우선 확인한다.
- DDR cascade 개발은 `qwen3.6-27b` + Singapore CosyVoice v3-plus 기준을 보존하되 Model 1–3 개발 비교를 잠시 중단한다. `qwen3.6-flash`와 27B를 active DDR 조건에 섞지 않는다.
- 중단 기간에는 새 voice source의 clean audio, consent/provenance, 정확한 전사·timed transcript, acoustic/CA annotation, persona registry와 voice enrollment reference package만 계속 준비한다.
- DDR 재개 시 optimistic latency claim 없이 first text/audio, full response, interruption latency를 다시 측정한다.

### 2026-09-14 — 3-layer Voice Agent prompt architecture

- `prompts/voice_agents/layer1_spoken_agent_base.md`에 Deepgram-style spoken-agent 기본 골격을 고정했다: 짧은 직접 응답, 자연스러운 음성, clarification, 불필요한 encyclopedia 설명·강제 closing 금지.
- `prompts/voice_agents/layer2_elf_policy.md`에 ELF 전략을 고정했다: meaning-first, clarification/confirmation/reformulation/accommodation, learner agency, 비원어민 오류·accent caricature 금지.
- `services/model1/prompts.py`의 단일 builder가 Layer 1 → Layer 2 → persona-specific Layer 3를 조합한다. Layer 3은 persona JSON에서 L1/proficiency/context/behavior/fictionalized 정보만 사용하며 rights/evidence/audio path/API secret은 제외한다.
- 직접적인 AI/실존 인물 질문에는 정직하게 disclosure하고, 비어 있는 hometown/private fact는 추측하지 않도록 했다. Deepgram Agent와 Qwen Model 1/2가 같은 prompt source를 재사용한다.
- 검증: 전체 테스트 **48 passed**, `py_compile` 성공.

### 2026-09-14 — F5-TTS / Fish Speech 검토 후보 기록

- F5-TTS와 Fish Speech/Fish Audio S2를 active classroom Voice Agent나 active DDR cascade가 아닌 self-hosted TTS 검토 후보로 기록했다.
- F5-TTS는 코드 MIT와 pretrained weights의 CC-BY-NC를 구분하고, Fish Speech는 Research License와 상업용 별도 license 필요성을 기록했다.
- 두 후보 모두 완전 무료로 표현하지 않고 GPU cloud/운영 비용과 custom Pipecat/LiveKit TTS adapter 필요성을 명시했다.

### 2026-09-14 — 교실 초기 운영을 managed Voice Agent로 전환

- 시간 제약과 cascade latency 문제를 반영해 초기 몇 주의 교실 적용은 Deepgram Voice Agent 또는 ElevenLabs Voice Agent 통합본으로 진행한다.
- Deepgram Voice Agent/Flux와 ElevenLabs Voice Agent는 DDR Model 1–3이 아니라 별도 운영 경로다.
- 기술보고서 상단에 공식 문서, Playground URL, Deepgram/NVIDIA benchmark, Pipecat 실제 지연 사례, LiveKit latency guidance를 기록했다.
- 공개 수치(예: 300–800ms 또는 특정 benchmark의 P50/P90)는 현재 환경의 보장값으로 사용하지 않으며, 실제 브라우저에서 first audible audio와 full response를 측정한다.

### 2026-09-14 — Deepgram resources용 CHN_004 interview package

- 사용자가 넣어 둔 `.deepgram_resources/ICNALE_SD_CHN_004_STUDENT_CLEAN.wav`는 그대로 두고, CHN_004 학생–인터뷰어 전체 대화 전사와 역할 자료를 `.deepgram_resources/`에 복사했다.
- `ICNALE_SD_CHN_004_interview_transcript.csv`는 canonical QC 전사(`xlsx_row`, task, `[T]/[S]`, text)이고, `ICNALE_SD_CHN_004_interview_transcript_role_labeled.csv`는 `Interviewer`/`Student` 역할로 명시한 240개 대화 행이다.
- `ICNALE_SD_CHN_004_segments_roles.csv`와 `ICNALE_SD_CHN_004_role_map.csv`도 함께 복사해 시간축·화자 역할을 연결했다. reference voice용 timed transcript/TXT/manifest도 별도로 복사했다.
- `.deepgram_resources/`를 `.gitignore`에 추가했다. 점(.) 폴더명은 숨김/추적 회피일 뿐 접근 제한이나 개인정보 보호 수단은 아니다.

### 2026-09-14 — Deepgram resources 최소화

- 사용자의 요청에 따라 `.deepgram_resources/`에는 핵심 두 파일만 남겼다: `ICNALE_SD_CHN_004_STUDENT_CLEAN.wav`와 `ICNALE_SD_CHN_004_interview_transcript_role_labeled.csv`.
- 중복 canonical transcript, role map, segments, transcript index, reference timed transcript/manifest는 해당 폴더에서 제거했다. 원본 자료는 `voices/.../03_qc`와 reference 폴더에 그대로 보존된다.

### 2026-09-14 — DDR cascade latency reduction plan

- 연구용 cascade의 latency는 classroom Voice Agent와 분리해 `user_turn_end → first_text_delta`, `user_turn_end → first_audio_chunk`, `response_end`를 각각 측정한다.
- 최적화 순서: Flux v2 turn-detection variant 비교, qwen3.6-27b quality baseline과 qwen3.6-flash low-latency ablation 분리, prompt/context 축소, 64–96 max token, clause-level Qwen→TTS overlap, connection/prewarm/audio-buffer 측정.
- 현재 27B + CosyVoice v3-plus의 일관된 1–2초를 보장하지 않으며, 연구용 현실 목표는 first audio 2–4초 범위로 둔다. 1–2초 교실 대화는 Deepgram Voice Agent 경로에서 별도로 검증한다.

### 2026-09-14 — Qwen Flash와 prompt-based speaker reproduction 정정

- `qwen3.6-flash`는 저지연 ablation/운영 후보로 사용할 수 있지만 Model 3 SFT base와 동일하게 취급하지 않는다. Model 3 fine-tuning 비교는 training 지원이 확인된 `qwen3.6-27b`를 기준으로 유지한다.
- System prompt/few-shot은 style probe와 빠른 가설 검증에는 유용하지만, 5–10개 예시만으로 개인 화자의 문법 오류·filler·hesitation·repair 분포를 고정밀 복제하거나 fine-tuning과 대등하다고 주장하지 않는다.
- 규칙을 늘릴수록 instruction conflict, 과잉 적용, 부자연스러운 오류, turn 간 drift가 생길 수 있으므로 source-grounded annotation과 held-out interaction test를 Model 3의 검증 조건으로 삼는다.

### 2026-09-14 — DDR source–chatbot correspondence 평가 추가

- Model 1의 voice enrollment/TTS가 음색은 복제해도 원본 학생의 WPM, pause, filler, hesitation, false start, repair, discourse habit을 자동 보존하지 않는다는 baseline 한계를 DDR 설계에 명시했다.
- `docs/0914 DDR_3D_GE.md`의 전문가 평가에 원본 reference audio와 chatbot audio의 대응성 평가를 추가했다.
- 새 평가 차원: timbre/identity, pronunciation/accent, speaking-rate/WPM, pause/rhythm, fluency behavior, lexical/syntactic/discourse habit, interactional behavior, over-smoothing risk, educational fit.
- fidelity와 educational appropriateness를 분리 점수화하고, Model 2 TTS LoRA·Model 3 delivery/profile 개선에서 over-smoothing gap이 줄어드는지 비교한다.

### 2026-09-14 — Model 1 전문가 검토 패키지 v0.2 준비

- 실제 CHN_004 quality sweep 14개 MP3를 `model1_artifact_manifest.csv`에 blinded `System_X`/`Voice_X` artifact로 등록했다.
- 전문가 rating 양식에 source–chatbot correspondence, pronunciation/accent, WPM, pause/rhythm, filler/hesitation/repair, discourse habit, over-smoothing, fidelity 항목을 추가했다.
- 총 14 artifact × 18 dimension = 252개 rating row를 생성했다.
- 다음 Model 1 단계는 전문가가 원본 reference audio와 chatbot audio를 함께 듣고 fidelity와 educational appropriateness를 분리 평가하는 것이다.

### 2026-09-14 — Model 1 baseline freeze 및 Model 2·3 개선 원칙

- 현재 Model 1을 Singapore Qwen3.6-27B + approved CHN_004 persona + Singapore CosyVoice v3-plus의 high-fluency baseline으로 동결한다.
- Model 2는 TTS LoRA를 통해 음색·발음·prosody·WPM·pause·rhythm을 개선하며 Qwen text fluency를 변경하지 않는다.
- Model 3 Qwen SFT/QLoRA도 자동으로 원본 학생의 낮은 구사력이나 말더듬을 재현하지 않는다. 승인된 text/CA annotation에 근거한 lexical-syntactic/discourse/repair/accommodation pattern과 delivery profile을 학습 대상으로 삼는다.
- 목표는 구사력을 인위적으로 낮추는 것이 아니라, source-grounded interactional habit을 보존하고 native-like over-smoothing을 줄이면서 intelligibility와 educational appropriateness를 유지하는 것이다.

### 2026-09-13 — Model Studio SFT 화면과 환경변수 운영 확정

- Model Studio Qwen fine-tuning 화면 `https://modelstudio.console.alibabacloud.com/ap-southeast-1/model/tuning`에서 `Qwen3.6-Open-Source` → `Qwen3.6-27B` snapshot을 Model 3 managed SFT 진입점으로 기록했다.
- Model 1과 Model 3의 primary base를 `qwen3.6-27b`로 맞추고, Model 1은 hosted inference, Model 3은 승인된 text JSONL 기반 SFT로 분리한다.
- `$env:NAME`은 현재 PowerShell 세션용 임시 설정이며, 애플리케이션용 영구 개발 설정은 `.env.local`에서 dotenv loader가 읽도록 한다.
- `.env.example`과 `.gitignore`를 추가해 API key와 credential CSV가 문서·source control에 포함되지 않도록 했다.

### 2026-09-13 — Model 1 hosted Qwen model 선택

- Model Studio model market에서 `qwen3.6-flash`와 `qwen3.6-plus-2026-04-02` 등 hosted model ID를 확인했다.
- Model 1 runtime은 일반 hosted inference model `qwen3.6-flash`로 우선 고정한다.
- Model market의 `qwen3.6-27b` Open-Source 항목은 Model 1 runtime이나 local Ollama용으로 선택하지 않는다.
- Open-Source 표시와 fine-tuning 가능 여부는 별개다. Model 3 fine-tuning에서는 Training 지원표의 model·region·method를 별도로 확인한다.

### 2026-09-13 — 공식 Training Overview 재확인 및 Qwen3.6-27B 선택 수정

- 최신 Model Studio `model-training-overview`에서 Singapore의 `qwen3.6-27b`가 `SFT Full Parameter Training`과 `SFT Efficient Training`을 모두 지원하는 것을 확인했다.
- 따라서 이전의 `qwen3.6-27b` 비선택 판단을 수정한다. `qwen3.6-27b`는 Model Studio hosted API로 호출할 수 있고, local Ollama 없이 Model 1 primary baseline 및 Model 3 SFT base 후보로 사용한다.
- `qwen3.6-flash`는 latency/연결 smoke test용 보조 모델로 둔다. Model market 노출과 Training 지원은 분리해서 판단한다.
- 근거: <https://docs.modelstudio.console.alibabacloud.com/en/model-studio/model-training-overview>.

### 2026-09-13 — 2609 Model 1과 2608 PNU Model 2·3 연계 계획

- `2609_CA-GELT_Choe`의 Model 1 cascade와 `2608_PNU`의 Gemini Live Model 1/2/3은 Model 번호·provider·연구 조건을 합치지 않는다.
- 2609에서 생산하는 turn/latency/error log, Style Card/persona 구조, pause·WPM·overlap·repair annotation, provenance 필드는 PNU Model 2·3의 참고 기술·분석 자산으로 이전한다.
- PNU Model 2에는 broad expert guide만 적용하고, PNU Model 3에는 Model 2 실제 learner–AI transcript, CA lens, structured expert feedback, Change ID가 있는 rule/context/memory decision만 반영한다.
- 두 프로젝트의 raw audio·transcript·reference clip은 양쪽 consent·secondary use·third-party cloud processing 범위가 확인된 경우에만 조건부 공유한다. provider credential과 participant memory는 공유하지 않는다.
- PNU의 이 연계 경계와 단계별 계획을 `2608_PNU/1. 2026프로젝트_부산대.md` §0.1에, 2609 관점의 이전 계획을 기술보고서에 반영했다.

### 2026-09-13 — Model 1 canonical persona registry (Phase 1)

- 중앙 경계를 `services/model1/personas.py`의 stdlib-only `PersonaRegistry`와
  `PersonaProfile`로 고정했다. `voices/personas/registry.json`은
  `persona_id`와 profile filename만 매핑하므로 ICNALE 전용 semantics를
  registry에 넣지 않는다.
- 첫 profile은
  `voices/personas/icnale_chn_004_student.json`이다. `source_grounded`에는
  repository에서 확인한 `ICNALE_SD_CHN_004`, `SPEAKER_01` Student 역할,
  clean-audio 처리 상태, 상대 provenance 경로만 기록했다. `fictionalized`는
  display label `CHN-004`와 source participant가 아닌 것으로 명시한 가상
  preferred name을 별도로 보관한다. accent marker, 개인 biography,
  stereotype는 만들지 않았다.
- CHN004의 consent/rights 및 permitted-use 범위는 metadata와 reference
  manifest에 따라 `pending`으로 유지한다. 연구·TTS·chatbot/public 범위를
  승인된 것으로 확장하지 않으며, rights evidence path가 확인될 때만
  해당 필드를 갱신한다.
- `Model1Cascade.from_config(..., persona_registry=registry)`와
  `run_persona(persona_id, task_context, audio_bytes)`를 추가했다. 기존
  `run(...)`은 유지하고, persona 경로는 profile의 `voice_id`를 TTS에,
  `prompt_context`를 Qwen의 명확한 `Persona Profile` system section에
  전달한다. profile/registry repr은 mapping, secret, raw audio를 출력하지
  않는다.
- 재현 절차는 다음 focused checks로 고정한다.
  `python -m pytest -q tests/test_model1_cascade.py` 및
  `python -m py_compile services/model1/personas.py
  services/model1/cascade.py services/model1/__init__.py`. 테스트에는
  registry resolution, missing-ID rejection, prompt inclusion, fake-backed
  `run_persona` voice/prompt propagation을 포함한다.
- 향후 source 일괄 적용은 (1) 동일한 네 section과 relative provenance로
  profile 작성, (2) source fact와 fictionalized identity 분리, (3) consent
  evidence 확인 전 pending 유지, (4) registry mapping 한 줄 추가, (5)
  fake-backed resolution/prompt test 추가 순서로 수행한다. provider adapter나
  source별 application route는 복제하지 않는다.

### 2026-09-14 — IDN_001/JPN_002 provisional processing

- CHN_004와 동일한 diarization export pipeline을 `ICNALE_SD_IDN_001`과
  `ICNALE_SD_JPN_002`에 적용했다.
- 두 source 모두 `SPEAKER_00=Interviewer`, `SPEAKER_01=Student` provisional
  mapping을 생성했다. 근거는 초기 diarization 순서와 transcript turn pattern이며,
  `final_review=PENDING`으로 유지했다.
- `model1_pilot/04_student_audio_pending/`에 두 화자의 speaker timeline,
  concatenated 후보 및 `*_STUDENT_PROVISIONAL.wav`를 생성했다.
- 역할 mapping과 video review가 확정되기 전에는 두 파일을 canonical TTS
  reference나 공개 chatbot voice로 사용하지 않는다. transcript에 explicit
  timing이 없으므로 matching reference text와 final clean audio는 만들지 않았다.
- 다음 재현 절차: 각 source의 `05_diarization/*_segments.csv`를 입력으로
  `scripts/export_diarized_audio.py`를 실행하고, `03_qc/*provisional_roles.csv`
  를 영상·전사와 대조한 뒤에만 `CONFIRMED`와 최종 student clean export로 승격한다.
- 중앙 persona registry에도 `icnale_idn_001_student`와
  `icnale_jpn_002_student` profile을 추가했다. 두 profile은 source-grounded
  facts와 fictionalized display identity를 분리하며, rights와 final audio review는
  계속 `pending`이다.

### 2026-09-14 — Deepgram Flux Kit/Kai classroom personas

- Deepgram Flux hosted voices `flux-kit-en` (British masculine)와
  `flux-kai-en` (Singaporean masculine)을 각각 `deepgram_kit`과
  `deepgram_kai` persona로 등록했다.
- Kit은 런던 출생·거주, 24세, University College London Applied Linguistics
  석사과정의 fictionalized classroom persona로 만들었고, Kai는 마닐라 출생·거주,
  23세, De La Salle University–Manila Business Administration 학부생으로 만들었다.
- `prompts/voice_agents/deepgram_kit.md`와
  `prompts/voice_agents/deepgram_kai.md`에 Layer 1 → Layer 2 → persona-specific
  Layer 3 최종 프롬프트를 저장했다. 두 프로필의 전기는 fictionalized이며 실제 음성
  소유자나 identity clone을 주장하지 않는다.
- hosted provider voice의 상업적 교실·공개 출력 범위는 약관 확인 전까지
  `RIGHTS_PENDING`으로 유지한다. 로컬 원본 음성이나 reference WAV는 등록하지 않았다.

### 2026-09-14 — Deepgram classroom persona profile enrichment

- `deepgram_kit`과 `deepgram_kai` profile에 education, daily routine, hobbies,
  personality, strengths, growth edges, values, learning motivation, cultural
  interests, conversation topics를 추가했다.
- Kit은 언어 변이·ELF·런던 생활을 중심으로, Kai는 소셜 엔터프라이즈·소규모
  사업·마닐라의 장소·교통·음식·실용적 일정 계획을 중심으로 대화 맥락을 확장했다.
- 확장된 JSON profile에서 Layer 1 → Layer 2 → Layer 3 정적 프롬프트를 다시
  생성하고, 두 파일이 shared prompt builder 결과와 일치함을 검증했다.

### 2026-09-14 — World Englishes persona portal frontend

- `prompts/deepgram_kit_code.json`과 `prompts/deepgram_kai_code.json`의
  generic phone-assistant prompt를 각 persona의 Layer 1 → Layer 2 → Layer 3
  prompt로 교체하고 Flux `v2` listen 설정을 유지했다.
- `apps/model1_web/static/index.html`에 Inner, Outer, Expanding Circle 포털과
  5개 persona 아이콘·링크를 추가했다.
- Kit, Kai, CHN-004, IDN-001, JPN-002에 고정 persona ID를 가진 별도 audio-first
  페이지를 만들었다. 학부/대학원 선택과 학번 입력은 frontend session memory에만
  보관하며 Apps Script는 아직 연결하지 않았다.
- 상세 페이지는 `text_delta`를 화면에 출력하지 않고 상태·음성만 보여 준다. 전체
  Python 테스트 49개, JavaScript syntax check, 6개 정적 route smoke test를 통과했다.

### 2026-09-14 — Deepgram Voice Agent integrated classroom path

- 교실의 `deepgram_kit`과 `deepgram_kai`는 기존 Qwen/CosyVoice cascade가 아니라
  `wss://agent.deepgram.com/v1/agent/converse` 단일 Deepgram Voice Agent 경로를
  사용하도록 연결했다.
- 각 persona의 저장된 Settings JSON에서 `flux-kit-en`/`flux-kai-en`,
  `flux-general-en` v2, managed Gemini `gemini-3.1-flash-lite`, 그리고 제작한
  Layer 1–3 prompt를 함께 전송한다.
- 브라우저 입력은 48 kHz Linear16 mono, Agent 출력은 24 kHz raw Linear16으로
  처리하며 ConversationText는 브라우저에 전달하지 않는다.
- `DEEPGRAM_AGENT_ENABLED=true`일 때만 이 경로를 활성화하고, Deepgram persona가
  legacy cascade로 우회되지 않도록 차단했다. Apps Script는 아직 연결하지 않았다.
- 검증: Deepgram Agent fake tests와 web tests 10개, 전체 Python tests 53개,
  JavaScript syntax check, Python compile 성공.

### 2026-09-14 — Deepgram classroom Apps Script transcript store

- `.env.local`에 `DEEPGRAM_AGENT_ENABLED=true`와 Agent timeout 설정을 추가했다.
- Deepgram Agent의 `ConversationText`를 화면에 렌더링하지 않는 bounded hidden
  transcript event로 변환하고, frontend가 설정된 Apps Script Web App URL로
  session/turn 데이터를 전송하도록 연결했다.
- `apps-script/Code.gs`를 추가했다. `Sessions`와 `AgentTranscript` 시트를 만들고
  persona/voice/model/deployment/degree/student ID/role/transcript를 영어 헤더로
  저장하며 중복 turn-role과 허용된 persona/voice를 검증한다.
- Apps Script는 STT나 provider 호출을 하지 않고 저장만 담당한다. 현재 두 페이지의
  `data-apps-script-url`은 빈 값이므로 `/exec` 배포 URL을 넣기 전에는 저장 요청을
  보내지 않는다.
- 추가 hidden-transcript forwarding test 포함 전체 Python tests **54 passed**,
  Apps Script JavaScript syntax check와 frontend syntax check 성공.
- `.env.local`의 실제 `DEEPGRAM_API_KEY`와 `DEEPGRAM_AGENT_ENABLED=true`로 Kit과
  Kai 각각의 Deepgram Agent 연결 smoke test를 실행했다. 두 persona 모두
  `settings_applied`, raw audio, hidden transcript, timing 이벤트를 수신했다.
- 배포된 Apps Script Web App health check가 성공했으며, Kit/Kai 페이지의
  `data-apps-script-url`을 해당 `/exec` URL로 연결했다. 브라우저 cross-origin
  POST는 Apps Script Web App 패턴에 맞춰 `no-cors` text request로 전송한다.

### 2026-09-14 — Audio-stage UI redesign

- 기존 plain HTML/default browser layout과 native audio control을 제거하고,
  World Englishes 포털과 persona pages를 dark responsive audio-stage UI로
  전면 재설계했다.
- root/nested static preview 모두 동작하도록 asset 경로를 상대 경로로 정리했다.
- Kit/Kai 페이지는 compact onboarding과 prominent Start/Stop controls,
  persona orb, 상태 패널만 노출하고 raw transcript와 native audio bar는 숨긴다.
- ICNALE placeholder pages도 같은 시각 시스템으로 맞췄으며, Deepgram Agent
  classroom 경로와 혼동하지 않도록 provider claim은 추가하지 않았다.
- JavaScript syntax check와 전체 Python tests **54 passed**.

### 2026-09-14 — Deepgram Agent barge-in protocol correction

- Deepgram Voice Agent의 공식 순서인 `Welcome → Settings → SettingsApplied →
  Media`를 지키도록 adapter handshake를 수정했다.
- 종료 시 지원되지 않는 `CloseStream` JSON을 보내지 않고 WebSocket을 직접 닫도록
  바꿨다.
- `UserStartedSpeaking` 수신 시 browser PCM playback을 즉시 중단해 barge-in을
  정상 처리한다.
- 수정 후 focused tests 12개와 실제 localhost Agent smoke test에서
  `Audio processing failed`/`Session error`가 발생하지 않음을 확인했다.

### 2026-09-14 — Kai classroom page verification

- Kai page `/personas/deepgram-kai/`의 고정 persona/voice/model과 Apps Script
  설정을 확인하고 중앙 포털의 Kai 링크를 검증했다.
- 실제 localhost Deepgram Agent smoke test에서 `settings_applied`, hidden
  transcript, `audio_done`, timing, stopped 이벤트를 수신했다.

### 2026-09-14 — Global Englishes studio language revision

- 중앙 화면을 `Global Englishes Studio`와
  `Intercultural Communication in Global Contexts` 중심으로 개편했다.
- syllabus, Rose et al. (2021), Lee et al. (2024)의 GE framing에 맞춰 WE, ELF,
  EIL, translanguaging/multilingual repertoires, GELT를 연결된 관점으로 설명했다.
- 세 circle 중심 탐색을 제거하고 다섯 persona를 현재 순서의 단일 목록으로
  표시했다. 개별 persona에는 circle을 부여하지 않고 위치, 이름, English
  context, 성별·연령·학업 상태만 간단히 노출한다.
- Kit/Kai 및 ICNALE 상세 페이지의 circle/fictional 문구를 제거하고 location +
  English communication 문구로 정리했다. 전체 Python tests **55 passed**와
  실제 localhost portal 렌더링을 확인했다.

### 2026-09-14 — Active Global Englishes partner list

- 메인 섹션 제목을 `Meeting Conversation Partners across Contexts`로 변경했다.
- 현재 활성화된 Kit과 Kai만 메인 카드로 노출하고, ICNALE 세 persona 링크는
  메인에서 제거했다.
- Kai 아래에 추가 conversation partners가 추후 확장될 것이라는 영어 안내
  문구를 추가했다. 전체 테스트 **55 passed**와 실제 포털에서 Kit/Kai 두 카드만
  표시되는 것을 확인했다.

### 2026-09-14 — Avatar and spatial-NPC extension scope

- `docs/1. GE-AI_technical-report.md`에 상반신 2D/2.5D avatar와 3D 공간 NPC
  확장 설계를 추가했다.
- 단일 정면 이미지 기반 prototype은 Deepgram audio/event layer 위에 붙이는
  시각 확장으로 정의하고, 실제 3D world는 WebGL/Unity, rigged GLB/VRM,
  proximity trigger, room/context/NPC logging이 필요한 별도 단계로 분리했다.
- 문화 공간은 국가·인종을 고정하는 배경이 아니라 상호문화적 활동 맥락과
  GE/ELF/EIL/GELT 수업 목표를 제공하도록 명시했다.

### 2026-09-15 — Kit/Kai base avatar placement

- 입·눈 overlay 정렬 결과는 runtime에 연결하지 않고, Kit과 Kai의 canonical
  base image만 상세 페이지의 기존 orbit 안에 배치했다.
- `apps/model1_web/static/avatars/kit.png`와 `kai.png`를 static asset으로
  복사하고 두 Deepgram persona 페이지의 orb를 image avatar로 교체했다.
- 상세 페이지 title도 `Global Englishes`로 통일했다.
- 실제 localhost Kit/Kai 페이지 렌더링과 전체 Python tests **55 passed**를
  확인했다.

### 2026-09-20 — Persona register scope correction

- Google Sheet `주차별 AI 페르소나`는 대화 챗봇 전사 저장소가 아니라
  주차별 persona provenance/register 전용이라는 사용자 확인을 반영했다.
- `apps-script/PersonaWeeklyCode.gs`에서 `Sessions`와 `AgentTranscript` 생성·
  저장 로직을 제거했다. 이 두 탭은 기존 `apps-script/Code.gs`의 legacy
  session/transcript 저장용이며 persona register endpoint에서는 사용하지 않는다.
- Persona register의 `doGet`은 `action=sync_personas&week=...` 요청만으로
  Kit/Kai 행을 생성·갱신하고, `doPost`는 `type=sync_personas` 요청만 받도록
  범위를 축소했다. 기존 Google Sheet에 남아 있는 Sessions/AgentTranscript
  탭은 코드가 자동 삭제하지 않는다.
- 기술보고서의 2026-09-20 기록도 같은 범위로 정정했다.

### 2026-09-20 — Persona register deployment verification

- 사용자가 `PersonaWeeklyCode.gs`의 새 Web App 배포를 완료했다고 보고했다.
- 제공된 `/exec` URL과 `action=sync_personas&week=3주차` 요청을 외부에서
  확인했으나 모두 HTTP 404 `Page not found`를 반환했다.
- 따라서 현재 해당 URL에서 persona register sync가 실행되었다고 주장하지
  않으며, 이번 확인으로 Google Sheet 데이터가 변경되었다고도 기록하지 않는다.

### 2026-09-20 — Persona register deployment verified

- 배포 화면의 정확한 deployment ID는 끝에 `w`가 포함된
  `...I4G6SVnA8w`였고, 이 정확한 `/exec` URL로 재확인했다. 앞선 404는
  끝의 `w`가 빠진 URL을 호출한 데서 발생했다.
- `GET /exec`가 `success: true`, `service: weekly-ai-persona-store`를
  반환했다.
- `GET /exec?action=sync_personas&week=3주차`를 실행해 `Sheet1`의 Kit과
  Kai 행을 모두 `updated` 상태로 갱신했다.

### 2026-09-20 — Deepgram Hannah/Naveen persona integration

- 사용자가 `prompts/raw_materials/`에 추가한
  `deepgram_Hannah_code.json`, `deepgram_Naveen_code.json`과
  `Hannah.png`, `Naveen.png`를 새 classroom persona source로 지정했다.
- `voices/personas/deepgram_hannah.json`과
  `voices/personas/deepgram_naveen.json`을 생성하고
  `voices/personas/registry.json`에 `deepgram_hannah`,
  `deepgram_naveen`을 등록했다. 두 profile은 Deepgram hosted voice
  metadata와 fictionalized classroom biography를 분리한다.
- `prompts/voice_agents_system-prompt/deepgram_hannah.md`와
  `deepgram_naveen.md`를 추가했다. 두 파일은 Layer 1 → Layer 2 →
  persona-specific Layer 3 구조를 따른다.
- `services/model1/deepgram_agent.py`에 두 raw settings와
  `flux-hannah-en`/`flux-naveen-en`을 등록하고,
  `services/model1/prompts.py`가 실제
  `voice_agents_system-prompt` 폴더를 읽도록 수정했다.
- 두 persona를 `apps/model1_web/server.py`의 integrated Deepgram Agent
  Model 1 경로에 등록했다. profile image와 static route도 추가했다.
- `apps-script/PersonaWeeklyCode.gs`의 weekly catalog에 두 persona를
  추가했다. 현재 classroom persona 네 개는 모두 Model 1이다.
- 검증: 전체 Python tests **57 passed**, JavaScript syntax,
  Apps Script syntax, 새 JSON parsing을 통과했다.

### 2026-09-21 — Deepgram voice provenance and weekly register update

- `voices/voice-sources.md`의 Deepgram Flux hosted classroom voice 표에
  `DEEPGRAM_FLUX_HANNAH_EN`과 `DEEPGRAM_FLUX_NAVEEN_EN`을 추가했다.
  두 source는 provider-hosted voice이며 identity clone이 아니고,
  `RIGHTS_PENDING`으로 유지한다.
- Hannah/Naveen의 fictionalized biography와 interaction style은
  `voices/personas/` profile과 Layer 3 prompt에서 관리하고, raw provider
  settings와 avatar image는 source material/visual asset으로 분리했다.
- 사용자가 제공한 Apps Script `/exec`에
  `action=sync_personas&week=3주차`를 실행했다. 응답은 `success: true`였지만
  `deepgram_kit`과 `deepgram_kai`만 `updated`로 반환되었고 Hannah/Naveen은
  반환되지 않았다. 따라서 현재 배포본에는 아직 새 두 catalog entry가
  반영되지 않은 것으로 판정하며, Sheet에 두 행이 추가되었다고 주장하지 않는다.

### 2026-09-21 — Weekly register cache-bypass verification

- 동일한 정확한 deployment URL의 이전 응답이 stale cached response였음을
  확인했다. cache-busting query parameter를 붙여 새 실행을 강제했다.
- 최신 응답은 `success: true`, sheet `주차별_로그`, week `3주차`였고,
  `deepgram_kit`/`deepgram_kai`는 `updated`,
  `deepgram_hannah`/`deepgram_naveen`은 `inserted`로 반환됐다.
- 따라서 Hannah와 Naveen의 3주차 persona 정보가 Google Sheet에 실제로
  추가된 것으로 기록한다.

### 2026-09-21 — Classroom persona deployment verification and push

- 실제 `.env.local` Deepgram credential로 `deepgram_hannah`와
  `deepgram_naveen`의 Agent handshake를 각각 실행했다. 두 persona 모두
  `ready`를 반환했고, voice model은 각각 `flux-hannah-en`과
  `flux-naveen-en`으로 확인했다.
- local WebSocket/static server smoke에서 `/`,
  `/personas/deepgram-hannah/`, `/personas/deepgram-naveen/`이 모두 HTTP
  200으로 응답했다.
- 전체 Python test suite는 **57 passed**였고, JavaScript·Apps Script
  syntax 및 JSON 검증도 통과했다.
- 변경 사항을 commit `71ea77b` (`Add Hannah and Naveen classroom personas`)로
  기록하고 `origin/master`에 push했다.

### 2026-09-20 — Weekly classroom AI-persona Google Sheets register

- Added the separate Apps Script deployment source
  `apps-script/PersonaWeeklyCode.gs`; existing `Sessions` and
  `AgentTranscript` endpoints remain separate from `apps-script/Code.gs`.
- The weekly sheet workflow locates the persona sheet by configured
  `PERSONA_SHEET_NAME`, exact `주차별 AI 페르소나`, or row-5 base headers, then
  fills/replaces G:Y while preserving A:F. A `session_start` upserts a
  deduplicated week + Model 1 + persona row, and `sync_personas` seeds or
  updates the current Kit/Kai catalog.
- Classroom default is Model 1 / Deepgram Voice Agent. New personas require
  explicit instruction plus catalog and application/provider mapping updates.
- Recorded the user-provided endpoint
  `https://script.google.com/macros/s/AKfycbzUwJatfsdDExxm5fUZlwg62FN8r-Z2D_IPLqVOnZwCn_ePh-72LAv7dmBlI4G6SVnA8/exec`;
  deployment status was not independently verified. `doGet` handles the
  one-time `action=sync_personas&week=...` request and `doPost` handles
  `session_start`/`agent_turn` storage updates. Deployment must use the new
  file as the endpoint source rather than combining duplicate handlers with
  the old `Code.gs`.
- The script embeds Kit/Kai metadata because Apps Script cannot read local
  repository JSON at runtime. Syntax parsing passed with `new Function(...)`;
  Apps Script deployment was not executed from this repository.
