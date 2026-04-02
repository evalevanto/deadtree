<p align="center">
  <img src="logo.svg" width="160" alt="deadtree">
  <br>
  <strong>deadtree</strong>
  <br>
</p>

<p align="center">
  Sync LaTeX projects with Overleaf. Free tier. Git-powered merges. No BS.
</p>

---

Overleaf charges you $$$$ for git sync. deadtree does it for free.

Your local git repo is the source of truth. An `overleaf/main` branch tracks what's on Overleaf. Pull merges. Push uploads. Conflicts are real git conflicts — resolve them with your editor, not some janky custom diff tool.

## Install

```bash
pip install deadtree
pip install 'deadtree[login]'   # first time only
playwright install chromium      # first time only
```

## 30 seconds to sync

```bash
deadtree init https://www.overleaf.com/project/abc123
deadtree login                    # browser pops up, log in, done
deadtree pull                     # grab everything from Overleaf
# ... write your paper ...
git commit -am "rewrote intro"
deadtree push                     # ship it
```

## Commands

| Command | What it does |
|---------|-------------|
| `deadtree pull` | Overleaf → local. Downloads, commits to `overleaf/main`, merges into your branch. |
| `deadtree push` | Local → Overleaf. Uploads changed files, updates `overleaf/main`. |
| `deadtree status` | What's different between you and Overleaf? |
| `deadtree diff` | `git diff` against Overleaf state. Colored. Contextual. Free. |
| `deadtree log` | Sync history. Every pull and push, timestamped. |

## Conflicts

Your coauthor edited the intro on Overleaf. You edited it locally. You pull.

```
$ deadtree pull
Merge conflicts detected. Resolve them, then:
  git add -A && git commit
```

That's it. It's a git merge. Use vim, vscode, meld, whatever. Fix the `<<<<<<<` markers, commit, push.

```
$ deadtree push
Done. 1 file(s) uploaded.
```

No interactive menus. No "pick a side" prompts. Just git.

## How it works

```
you           ──●──●──●──────●── your branch
                       \    /
overleaf/main ──●───●───●──      what Overleaf has
                pull  pull
```

- `pull` downloads the Overleaf zip, commits it to `overleaf/main` (without touching your working tree), then `git merge`s into your branch
- `push` uploads your diff, then re-downloads to keep `overleaf/main` in sync
- `status` and `diff` are just git commands against the two branches

The git plumbing uses a temporary index to commit to `overleaf/main` without checkout. Your working tree is never disturbed.

## Config

```bash
deadtree init https://www.overleaf.com/project/YOUR_PROJECT_ID
```

Writes `.overleaf.json`. That's the only config.

## Why not just use Overleaf's git integration?

It costs money. deadtree is free. Also deadtree gives you proper branching, local git history, and works with any git workflow you already have.

## License

MIT. Do whatever you want.
