#!/bin/bash
# The sandbox never persists .git/config (credential-path exclusion) and may
# drop .git/refs — run this BEFORE any git command after a session restore.
cd "$(dirname "$0")/.." || exit 1
mkdir -p .git/refs/heads .git/refs/tags
if [ ! -f .git/config ]; then
cat > .git/config <<'CFG'
[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true
[user]
	name = nixfav-engine
	email = engine@users.noreply.github.com
[remote "origin"]
	url = https://github.com/holymusic1020/Cringe_yt_a_cong_collections_of_Public_songs_i_liked_justy_random-m_name_so_peoble_donmt_find_it_lol.git
	fetch = +refs/heads/*:refs/remotes/origin/*
CFG
fi
git config user.name  >/dev/null 2>&1 || git config user.name  "nixfav-engine"
git config user.email >/dev/null 2>&1 || git config user.email "engine@users.noreply.github.com"
git remote get-url origin >/dev/null 2>&1 || \
  git remote add origin "https://github.com/holymusic1020/Cringe_yt_a_cong_collections_of_Public_songs_i_liked_justy_random-m_name_so_peoble_donmt_find_it_lol.git"
git log --oneline -1 || echo "WARN: no history"
