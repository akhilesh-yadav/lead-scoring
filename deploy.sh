# Deploy to Google Cloud Run
gcloud run deploy lead-scoring-poc \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8501 \
  --memory 1Gi \
  --cpu 1

# Or deploy to Render (render.yaml in repo root)
# Or deploy to Railway: railway up
# Or deploy to Fly.io: fly launch && fly deploy
