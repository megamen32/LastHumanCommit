# ZCode LHC hook-loader runtime evidence — 2026-10-26

## Source and installed loader

- Canonical source: LastHumanCommit at `faba4cf018871cc137e1ee1d175a02409d0f5603`; source package declares LHC plugin `1.5.43`.
- Canonical package validation: `sync_skills.py --check` passed (25 skills); plugin `validate.py` passed.
- Native ZCode plugin manager updated enabled `last-human-commit@last-human-commit` from broken `1.0.0` to `1.5.43`; installed root is `~/.zcode/cli/plugins/cache/last-human-commit/last-human-commit/1.5.43`.
- Cause: old manifest expanded unset `PLUGIN_ROOT` to `/tools/lhc_time_guard.py`; both SessionStart and UserPromptSubmit were blocked with file-not-found. Updated package registers the supported SessionStart instruction hook and does not register the stale UserPromptSubmit time-guard command. The disabled `fleet-lhc` plugin remains disabled.
- The unrelated local marketplace advertised `1.5.65`, but native manager update reported already up to date at `1.5.43`; no marketplace cache or installed files were manually changed.

## Fresh native model response

- Fixture: ZCode `session_ee676342-13d2-4f96-bbe1-d76101edb18e`, host `roomhacker-server-100`, model `account:zai-individual-coding-plan/GLM-5.3-Flash$high`.
- Stable input: `hf26-zc-lhc-loader-answer-20261026-01`; Herder job `job_61a828d92c5f365a19b6605b9f6d3ff1948f2ce5bfb7617837d11ae1733f2056` completed and native turn `turn_700c56cc-05ef-4b3b-8689-406944c07797` completed.
- Native history contains the exact final marker `LHC_ZCODE_HOOK_MODEL_OK` and a concrete README/code mismatch: README documents `ENABLE_QODER` default false, while `src/index.ts` uses true.
- Native lifecycle evidence after update: SessionStart LHC hook receipts `.6.0` and `.7.0` succeeded. The UserPromptSubmit event chain succeeded; the obsolete LHC UserPromptSubmit time-guard hook is absent.

## First timing-ambiguous queue attempt

- First input `hf26-zc-lhc-active-seed-20261026-01`, job `job_a7df59ef39257cbaacd7e87898a4af073dd0073cc866309b340e1898647691bd`, completed with marker `ZC_ACTIVE_TURN_READY`; its native turn was observed running as `turn_7840b7fd-1366-4214-b23b-be3cf2ea32b1` before the queue send call. This does not prove it was still running at native command admission.
- Queue input `hf26-zc-lhc-queued-proof-20261026-01`, job `job_a3f09e239499b7a2c9e558e303113d681021c91947b32e249d4185ec048b3359`, reached a terminal non-retryable receipt: `admitted=true`, `ok=false`, error `ZCode принял сообщение в другом режиме (startNow вместо queue); повторная отправка запрещена.` The response text includes `ZC_NATIVE_QUEUE_PROCESSED`, but it is not proof of queue admission.
- Independent native queue readback after the failed contract: `nativeState=completedSuccess`, `autoDrain=true`, `pendingCount=0`, revision `217`, `canResume=false`. No queue resume was attempted and the admitted input was not replayed.
- Result: LHC hook loader/model response passed. Queue acceptance is not proven: native accepted `startNow` instead of requested `queue`; exact receipt retained, no retry. The active turn may have completed between the running observation and native admission, and the predispatch `inputRouting` snapshot was not captured, so the cause remains unknown.

### Queue delivery route details

- Herder's queue request is wired in `agent-herder/src/adapters/zcode.ts`: `sendConversationInput` sets `requestedDelivery` to `queue` when `steer=false` (line 2396) and passes it in V4 `sendText.payload` (lines 2445–2452). The adapter validates the native `inputAccepted.delivery` and fails closed on mismatch (lines 2481–2484).
- Installed `/home/roomhacker/.zcode/server/zcode-server.cjs` accepts `sendText.requestedDelivery` values `startNow|queue|guide` (lines 204916–204924), defines `inputRouting.mode` as `startNow|enqueue|guide|reject|choice` (lines 183406–183410), and separately supports `setAutoDrain` (205010). Its `sendConversationCommandV4` service route forwards the command to the native service (206107+ and 219206+). There is no separate queue-only send command in this supported V4 surface; queue admission is determined by native routing.
- The native SQLite `session_input` row for `queue_hf26-zc-lhc-queued-proof-20261026-01` records `delivery=startNow`, `status=promoted`, `promotedMessageId=msg_mvoz2i14_78393ff3-1f0a-4941-a033-6b5d898aef25`; its intent records `sourceCommandId=hf26-zc-lhc-queued-proof-20261026-01`, `requestedDelivery=startNow`, `admittedDelivery=startNow`, `admissionSeq=2`. This agrees with the Herder nonretryable mismatch receipt.
- For this first attempt, the predispatch `inputRouting` object and native status at the exact command-admission instant were not captured. Herder had confirmed a native active turn ID and `running` status before the send call, but that read does not expose `inputRouting`; the native receipt arrived later and the available snapshot is terminal. The turn may have completed before native admission. A separate decisive attempt with exact live routing and active Bash evidence is documented below.


## Decisive active queue attempt — 2026-10-26

- Exact fixture owner: `session_ee676342-13d2-4f96-bbe1-d76101edb18e`, PID 3371132 / generation 1, workspace `/home/roomhacker/agents-projects/agent-herder`.
- Before the seed, native V4 `setAutoDrain(false)` used query-first stable command `hf26-zc-set-autodrain-off-20261026-01`; accepted at revision 217, read back revision 218 with `autoDrain=false`, pending 0, `completedSuccess`, same owner.
- Distinct seed `hf26-zc-active-45s-seed-20261026-01`, job `job_aebf3f7d5e4612412a967b29b93dd2a0bd88b1b0e744b65b4bb95412cf5d52a0`, was admitted once and reported pending. During its active turn the official V4 snapshot at 2026-10-26T08:17:41.407Z showed turn `turn_eaafc71e-7762-432e-90b4-23e14741ec4f`, `inputRouting={mode:enqueue}`, `nativePhase=running`, `autoDrain=false`, pending 0, and a running native `Bash` tool. Same official native owner was confirmed.
- Only after that snapshot, distinct queue input `hf26-zc-active-enqueue-20261026-01` was sent once. Herder job `job_7eb954d52a494228db2c8b30df6ce7956a28f481399087ec760633bb304a43ee` finished with `admitted=true`, `ok=false`, `nonRetryable=true`, error `ZCode принял сообщение в другом режиме (startNow вместо queue); повторная отправка запрещена.`
- Native read-only SQLite row `queue_hf26-zc-active-enqueue-20261026-01` records `delivery=startNow`, `status=promoted`, promoted message `msg_mvozifb9_8868e007-5cf3-4551-9623-9eea687fbfc1`, `requestedDelivery=startNow`, `admittedDelivery=startNow`, `admissionSeq=4`. Native final turn `turn_81034ec4-58c9-42b8-b5ac-68cd0a3e68de` completed and the response ends in `HF26_ZCODE_ENQUEUE_FINAL_OK`; this is a model response to the accepted startNow input, not queue acceptance.
- Final exact queue readback: `completedSuccess`, `autoDrain=false`, pending 0, revision 450, `canResume=false`. No resume was called because no queue item exists; no input was replayed.
- Proven result: a queue request sent after a native snapshot with `inputRouting=enqueue` and a running Bash tool was accepted by the native path as `startNow`; Herder correctly surfaced the mode mismatch and prohibited retry. Queue processing acceptance/final-after-resume is not proven. The reason the native route converted it is not established; no native core edits were made.
