# Sample leaf images

Drop 3–4 real leaf photos here for the demo (do NOT fabricate images).

Recommended source: the PlantVillage dataset (https://www.kaggle.com/datasets/emmarex/plantdisease)
— pick images of:
- rice brown planthopper damage / hopper burn
- rice blast lesions
- a healthy leaf (negative control)

Any `.jpg`/`.png` under 8 MB works with `POST /api/diagnose`.
In DEMO_MODE the canned diagnosis is returned regardless of the image;
with a real `GEMINI_API_KEY` (DEMO_MODE=0) Gemini vision analyzes the actual photo.
