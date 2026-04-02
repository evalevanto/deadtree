# 🪵 deadtree

Sync local LaTeX projects with Overleaf. Because papers are dead trees.

Free-tier compatible. Git-powered conflict resolution.

<p align="center">
  <img src="logo.svg" width="128" alt="deadtree logo">
</p>

## Install

```bash
pip install deadtree                 # core
pip install 'deadtree[login]'        # + browser login
playwright install chromium           # one-time setup
```

## Usage

```bash
deadtree init https://www.overleaf.com/project/abc123
deadtree login        # opens browser, one-time auth
deadtree pull         # Overleaf → local (git merge)
deadtree push         # local → Overleaf
deadtree status       # what's different?
deadtree diff         # git diff against Overleaf
deadtree log          # sync history
```

## How it works

deadtree uses your local git repo as the sync engine:

- An `overleaf/main` branch tracks what's on Overleaf
- `pull` downloads from Overleaf, commits to `overleaf/main`, merges into your branch
- `push` uploads your changes, updates `overleaf/main`
- Conflicts are real git merge conflicts — resolve with your normal tools

No custom merge logic. No manifest files. Just git.

```
main          ──●──●──●──────●── (your work)
                       \    /
overleaf/main ──●───●───●──     (Overleaf state)
                pull  pull
```

## Conflict resolution

```
$ deadtree pull
Merge conflicts detected. Resolve them, then:
  git add -A && git commit

$ vim main.tex      # fix the conflict markers
$ git add -A && git commit
$ deadtree push     # upload resolved version
```

## Config

`deadtree init` writes `.overleaf.json`:

```json
{
  "project_id": "abc123",
  "paper_dir": "."
}
```

## License

MIT
