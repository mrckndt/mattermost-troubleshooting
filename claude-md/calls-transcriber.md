### calls-transcriber

**What**: Live-captions and post-call transcription worker for Mattermost Calls
**Stack**: Go, whisper.cpp, Azure Speech, Silero VAD, Opus codec, WebRTC (pion)
**Min server / min plugin**: Mattermost >= v7.8, mattermost-plugin-calls >= v0.19.0

**Pipeline reference**: end-to-end transcription flow + cross-component version matrix in `claude-md/mattermost-plugin-calls.md > Calls pipeline reference`.

**Configuration (env vars)**:

| Field | Values | Default | Purpose |
|---|---|---|---|
| `TRANSCRIBE_API` | `whisper.cpp` / `azure` / `openai/whisper` | `whisper.cpp` | Provider |
| `MODEL_SIZE` | `tiny` / `base` / `small` / `medium` / `large` | `base` | Whisper model for post-call |
| `LIVE_CAPTIONS_ON` | `true` / `false` | `false` | Enable live captions |
| `LIVE_CAPTIONS_MODEL_SIZE` | as above | `tiny` | Smaller model = lower latency for live |
| `LIVE_CAPTIONS_LANGUAGE` | ISO 639-1 | `en` | Caption language |
| `NUM_THREADS` | 1..numCPU | auto | Threads for post-call transcription |
| `TRANSCRIBE_API_OPTIONS` | JSON | - | Provider-specific options (Azure key/region) |

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Configuration & validation | `cmd/transcriber/config/config.go` |
| Core transcriber logic | `cmd/transcriber/call/transcriber.go` |
| Track processing & post-call transcripts | `cmd/transcriber/call/tracks.go` |
| Live captions processing | `cmd/transcriber/call/live_captions.go` |
| whisper.cpp backend | `cmd/transcriber/apis/whisper.cpp/context.go` |
| Azure Speech backend | `cmd/transcriber/apis/azure/speech_recognizer.go` |
| Output formats (WebVTT, text) | `cmd/transcriber/transcribe/` |

### Common Investigation Patterns

**Missing models**: Models mounted at `/models/ggml-{tiny,base,small,medium,large}.bin` (post-call) and `silero_vad.onnx` (VAD). Set `MODELS_DIR` env var if a different path is used. Validation in `whisper.cpp/context.go` fails with `invalid ModelFile: failed to stat model file`.

**Slow or missing transcripts**: Verify `LIVE_CAPTIONS_ON=true`, `NUM_THREADS` reasonable for the host (capped at `numCPU`), and that the chosen model fits in available memory. Live captions default to `tiny` for latency; post-call defaults to `base`. Force a language by setting it explicitly - whisper auto-detection can be slow on noisy audio.

**Transcription upload fails or posts missing**: Check API connectivity and auth token. Output is written to `/data/{transcriptionID}/{filename}.{vtt,txt}`. Azure requires `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` in `TRANSCRIBE_API_OPTIONS` JSON. The container needs both `/data` and `/models` volumes mounted.

### Calls-Transcriber Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `invalid ModelFile: failed to stat model file` | Model file not found | Verify `/models/ggml-<size>.bin` exists; check `MODELS_DIR` |
| `NumThreads should be in the range [1, N]` | `NUM_THREADS` exceeds CPU count or is 0 | Set within `1..nproc` |
| `failed to create speech detector` | Silero VAD model missing or corrupt | Ensure `silero_vad.onnx` in `/models` |
| `failed to create opus decoder` | Codec init failed | Confirm audio format is Opus |
| `failed to post transcription` | API or auth failure after retries | Check `SITE_URL`, `AUTH_TOKEN`, server reachability |
| `LiveCaptionsModelSize value is not valid` | Invalid live-caption model size | Use one of tiny / base / small / medium / large |
| `failed to decode audio data for live captions` | Corrupted Opus packet | Often indicates RTC connection instability; check call logs |
