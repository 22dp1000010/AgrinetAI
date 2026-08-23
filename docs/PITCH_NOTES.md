# Pitch Notes

## 2–3 line description (submission field)

> AgriNet is a federated agricultural intelligence network: every Indian state runs its own node on a shared open protocol, giving farmers grounded, voice-first advisories in their language from satellite, soil, weather and Gemini. When one state's node detects a disease outbreak, neighbouring states get an early warning automatically — cooperation built into the infrastructure. One container per state, open schema, deployable in weeks: a digital public good.

## Slide skeleton (10–12 slides)

1. **Title** — AgriNet: a federated agricultural intelligence network. Team, track (Problem 04, Cooperation).
2. **Problem** — 86% of Indian farmers are small/marginal; advisories are generic, English-first, and states can't share outbreak signals. (Quote the problem statement.)
3. **Solution overview** — one screenshot each: farmer advisory with provenance strip, diagnosis card, Odisha dashboard with "Early warning from Telangana" banner.
4. **How the AI works** — the advisory pipeline diagram: satellite + soil + weather + RAG → one Gemini call → cited, structured, multilingual advisory. Gemini vision for diagnosis. Emphasize: grounded, citations mandatory, no invented dosages.
5. **The differentiator: federation** — AgriNet Protocol v1 (open schema). Live demo fact: two Cloud Run nodes exchanging alerts over the public internet. Model registry = states sharing fine-tuned Gemma models.
6. **Demo money-shot** — 3 diagnoses in Warangal → alert appears on the Odisha node. "Cooperation is not a slide in our deck; it's an API call."
7. **Built for India** — Telugu/Hindi/English, voice-first (Web Speech), mobile-first, low-bandwidth, works on cached data when offline. District-level privacy.
8. **Deployability** — one container per state (`gcloud run deploy`), scale-to-zero, ≈ $15–35/month per state pilot. SQLite→Firestore swap-ready. Pilot in weeks, not years.
9. **Reach & impact** — path: 1 district → 1 state → 28 states. Each node serves every farmer with a phone; the federation multiplies value with each new state (network effects for food security).
10. **Real data** — live SoilGrids + Open-Meteo, Sentinel-2 NDVI, ICAR advisory corpus (placeholders to be replaced with verbatim extracts — note honestly).
11. **Roadmap** — WhatsApp/IVR, offline Gemma at KVKs, signed federation envelopes, BigQuery analytics.
12. **Ask / close** — "Any state deploys a node with one container. The protocol is open. This is a digital public good."

## Judging-criteria mapping

| criterion | weight | our answer |
|---|---|---|
| AI/Technical Execution | 25% | Gemini visibly does the reasoning (advisory JSON), vision (diagnosis), multilingual output; end-to-end works live + DEMO_MODE safety net |
| Problem-Solution Fit | 20% | every clause of the challenge is a feature: regenerative recs ✓ satellite/soil/weather ✓ disease diagnostic ✓ interoperable network ✓ DPG ✓ |
| Depth & Reach Across India | 20% | federation = the scaling story; add a state by deploying one container |
| Deployability & Scalability | 20% | Cloud Run, scale-to-zero, ≈$15–35/state/month, pilot in weeks |
| Impact Potential | 15% | early warnings cross borders before pests do; voice + local language reaches low-literacy farmers |

## Video beats (3–5 min, follow README demo script)

0:00 problem in one breath → 0:30 farmer advisory (provenance strip!) → 1:30 Telugu + voice → 2:15 leaf diagnosis + safety note → 2:45 outbreak triggers → 3:15 Odisha node banner (the money-shot, slow down here) → 4:00 federation panel + architecture → 4:30 close on DPG line.

**Before recording:** warm all Cloud Run services (`curl /v1/health`), run the seed script, set DEMO_MODE=1 as the safety net, record real Gemini responses in rehearsal if using live mode.

## Honest-notes (don't get caught)

- Corpus files are clearly-marked placeholders — replace with verbatim ICAR/PJTSAU/OUAT extracts before submission.
- te/hi UI strings are machine translations — get a native speaker to review.
- Satellite features are pre-computed snapshots (real Sentinel-2 pathway exists behind `EE_ENABLED`); say "cached satellite features, live provider implemented" if asked.
- Registration deadline: **Mon 24 Aug 2026** — register now if not done.
