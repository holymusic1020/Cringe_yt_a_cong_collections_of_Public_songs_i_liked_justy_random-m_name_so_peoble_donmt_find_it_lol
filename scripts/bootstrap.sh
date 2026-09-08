#!/usr/bin/env bash
# Local-sandbox bootstrap (GitHub Actions installs its own deps in the workflow)
set -e
command -v ffmpeg >/dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg fonts-dejavu-core; }
pip install -q edge-tts yt-dlp pillow requests
echo "bootstrap done: ffmpeg=$(ffmpeg -version | head -1 | awk '{print $3}') edge-tts=$(python3 -c 'import edge_tts; print(edge_tts.__version__)')"
