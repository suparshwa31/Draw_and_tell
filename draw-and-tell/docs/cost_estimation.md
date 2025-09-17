# Operations & Metrics Guide

This document outlines performance metrics, cost estimates, fallback strategies, and S3 storage for the **AI-powered multimodal system** (CV, ASR, TTS).

---


## 1. Latency Estimates (per component)

| Component | Model                                                 | Typical Latency (GPU) | Typical Latency (CPU) |
| --------- | ----------------------------------------------------- | --------------------- | --------------------- |
| CV        | `blip-image-captioning-base`                          | 1–3 s                 | 10–15 s               |
| ASR       | `whisper-small`                                       | 10–30 s (3-min audio) | >1 min                |
| TTS       | `speecht5_finetuned_single_speaker_de_small_librivox` | 0.5–3 s               | 1–5 s                 |

> **Note**: First TTS latency can be reduced using pre-generated or canned audio while the main inference happens in the background.

---

## 2. Cost Estimation

### Assumptions

* 100 sessions × 3 minutes each = 5 hours total runtime
* Using cloud GPUs (T4/A10G) for inference
* Hugging Face endpoints included

### Approximate Costs

| Setup                                    | Estimated Cost / 100 sessions |
| ---------------------------------------- | ----------------------------- |
| Prototype (single T4 GPU)                | \$3–6                         |
| Production (separate LLM + ASR/TTS GPUs) | \$10–25                       |


---

## 3. Fallback Strategies

1. **ASR fallback**

   * Retry with smaller Whisper model or CPU fallback
   * UX fallback: prompt user to repeat or provide text input

2. **TTS fallback**

   * Play pre-recorded canned messages if model fails or is slow
   * Regenerate full message in background

3. **LLM fallback**

   * Use templated responses or small lightweight model if main LLM times out
   * Queue request and display conservative reply

4. **Degrade gracefully**

   * Run CV on CPU if GPU unavailable
   * Serve short canned TTS while waiting for full inference

5. **Monitoring & Alerts**

   * Track ASR confidence, latency spikes, and error rates
   * Trigger autoscaling or alert on-call if thresholds breached

---

## 4. S3 Storage

1. **Encription**
    *All scanned images will be stored in an S3 bucket with server-side encryption (SSE) to ensure data confidentiality*

2. **Access Control**
    *Access to stored images will be restricted using AWS IAM policies. Authorized parents can access their child’s drawings through pre-signed URLs, providing secure and temporary access without the need to manage individual keys*

3. **Retention**
    *A lifecycle policy will be implemented to automatically delete session data after a defined retention period. Versioning can be enabled to allow recovery from accidental deletions, ensuring secure and compliant data management*

---

## 5. Additional notes
- Currently, local storage is used for audio and image data. In production, Amazon S3 with the above practices is recommended.
- Models have been optimized for CPU; GPU usage will improve performance significantly.
- Batch processing can further reduce inference time when multiple images are uploaded in parallel.
- Small model versions are used for this implementation; larger models can improve accuracy and quality in production.
