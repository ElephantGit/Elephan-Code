import os
import json
import tempfile
from elephan_code.utils.trajectory import TrajectoryRecorder


def test_trajectory_json():
    tmpdir = tempfile.TemporaryDirectory()
    out_dir = os.path.join(tmpdir.name, "runs")
    rec = TrajectoryRecorder(save_dir=str(out_dir), fmt="json")
    rec.start("t1")
    rec.record_thought("thinking")
    rec.record_action("a", {"p": 1})
    rec.record_observation("ok")
    rec.end(status="done")

    files = os.listdir(out_dir)
    assert len(files) == 1
    path = os.path.join(out_dir, files[0])
    content = json.loads(open(path, encoding='utf-8').read())
    assert content["task"] == "t1"
    assert any(e["phase"] == "action" for e in content["events"]) 


def test_trajectory_jsonl():
    tmpdir = tempfile.TemporaryDirectory()
    out_dir = os.path.join(tmpdir.name, "runs2")
    rec = TrajectoryRecorder(save_dir=str(out_dir), fmt="jsonl")
    rec.start("t2")
    rec.record_thought("thinking")
    rec.record_action("a", {"p": 2})
    rec.record_observation("ok")
    rec.end(status="done")

    files = os.listdir(out_dir)
    assert len(files) == 1
    path = os.path.join(out_dir, files[0])
    text = open(path, encoding='utf-8').read().splitlines()
    assert len(text) >= 2
    header = json.loads(text[0])
    assert header.get("task") == "t2"
