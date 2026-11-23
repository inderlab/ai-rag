# n8n workflows

Two workflows to import into n8n (Workflows → Import from file).

## 1. Video ready notification (`video_ready_notification.json`)

`Webhook → IF event == video.ready → Telegram (ready) / Telegram (failed)`

VidMind calls this webhook when a video finishes (`ready`) or fails (`failed`).

1. Import the file, add your Telegram bot credential, replace `YOUR_TELEGRAM_CHAT_ID`.
2. Activate the workflow and copy the production webhook URL.
3. In `backend/.env`:
   ```
   N8N_WEBHOOK_URL=http://localhost:5678/webhook/vidmind-video-ready
   PUBLIC_APP_URL=http://localhost:5173
   ```

Payload sent by the backend:

```json
{
  "event": "video.ready",
  "video": {"id": 2, "youtube_id": "zjkBMFhNj_g", "title": "...", "status": "ready",
            "error": null, "chunk_count": 49, "url": "...", "app_url": "http://localhost:5173/videos/2"},
  "insights": {"title": "...", "summary": "...", "tags": ["..."], "chapters": [{"start": "00:00", "title": "..."}]}
}
```

## 2. YouTube channel watcher (`youtube_channel_watcher.json`)

`Every 6 hours → Config → Channel RSS → Only new uploads → POST /api/videos`

Reads the channel's public RSS feed (`https://www.youtube.com/feeds/videos.xml?channel_id=...`) and adds every video published in the last 6 hours to VidMind. When it is ready, workflow 1 sends the Telegram message.

If the backend runs with `AUTH_REQUIRED=true`, add a header `Authorization: Bearer <token>` to the **Add to VidMind** node (token from `POST /api/auth/login`).

Edit the **Config** node: `channel_id`, `api_url` (`http://host.docker.internal:8000/api` when n8n runs in Docker, `http://localhost:8000/api` otherwise) and `hours`.

## Run n8n locally

```bash
docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

The JSON structure is checked by `backend/tests/test_n8n_workflows.py`.
