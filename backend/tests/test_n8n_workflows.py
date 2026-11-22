import json
from pathlib import Path

import pytest

N8N = Path(__file__).resolve().parents[2] / "n8n"
FILES = sorted(N8N.glob("*.json"))


def test_two_workflows_exist():
    assert {f.name for f in FILES} == {
        "video_ready_notification.json",
        "youtube_channel_watcher.json",
    }


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_workflow_is_valid(path):
    wf = json.loads(path.read_text())
    names = [n["name"] for n in wf["nodes"]]
    assert len(names) == len(set(names))
    for node in wf["nodes"]:
        assert node["type"].startswith("n8n-nodes-base.")
        assert {"id", "parameters", "typeVersion", "position"} <= set(node)
    for source, outputs in wf["connections"].items():
        assert source in names
        for branch in outputs["main"]:
            for link in branch:
                assert link["node"] in names
    linked = {link["node"] for o in wf["connections"].values() for b in o["main"] for link in b}
    starts = [n for n in names if n not in linked]
    assert len(starts) == 1


def test_webhook_path_matches_docs():
    wf = json.loads((N8N / "video_ready_notification.json").read_text())
    hook = next(n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.webhook")
    assert hook["parameters"]["path"] == "vidmind-video-ready"
    assert "vidmind-video-ready" in (N8N / "README.md").read_text()


def test_watcher_posts_to_videos_api():
    wf = json.loads((N8N / "youtube_channel_watcher.json").read_text())
    http = next(n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.httpRequest")
    assert http["parameters"]["method"] == "POST"
    assert http["parameters"]["url"].endswith("/videos")
