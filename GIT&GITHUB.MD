# Git Best Practices

---

## Core Commands You'll Use Daily

```bash
git status                    # see what changed
git add .                     # stage everything
git add <file>                # stage one file
git commit -m "message"       # commit staged changes
git push origin <branch>      # push to remote
git pull origin <branch>      # pull latest changes
git log --oneline             # see commit history (compact)
git diff                      # see unstaged changes
```

---

## Branching

### How to create a branch

Always branch off from the latest `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/user-login
git switch -c feature/user-login     #checkout    or switch  both will work

```

### Branch naming convention

```
<type>/<what-it-does>
```

| Type | When to use | Example |
|---|---|---|
| `feature/` | Adding something new | `feature/user-login` |
| `fix/` | Fixing a bug | `fix/login-redirect` |
| `hotfix/` | Urgent production fix | `hotfix/crash-on-payment` |
| `chore/` | Config, deps, cleanup | `chore/update-packages` |
| `docs/` | Documentation only | `docs/api-guide` |
| `refactor/` | Restructuring code | `refactor/auth-module` |

**Rules:**

- Lowercase only, use hyphens — no spaces or underscores
- Keep it short and readable
- One branch = one job. Never mix unrelated changes.

---

## Sub-branches (branches off a feature branch)

If a feature is large, you can branch off the feature branch itself:

```bash
# You're working on a big user-auth feature
git checkout -b feature/user-auth

# A team member takes the frontend part
git checkout feature/user-auth
git checkout -b feature/user-auth-ui

# Another handles the backend
git checkout feature/user-auth
git checkout -b feature/user-auth-api
```

Once both are done, merge them back into `feature/user-auth`, then merge that into `main`.

```
main
 └── feature/user-auth
      ├── feature/user-auth-ui
      └── feature/user-auth-api
```

---

## Commit Messages

### Format

```
<type>: <short description>
```

**Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`

### Examples

```bash
# Good
git commit -m "feat: add login form validation"
git commit -m "fix: handle null response from user API"
git commit -m "docs: update README with setup steps"
git commit -m "chore: upgrade eslint to v9"
git commit -m "refactor: simplify auth token logic"

# Bad
git commit -m "fix stuff"
git commit -m "wip"
git commit -m "changes"
git commit -m "asdf"
```

### Rules

- Write in present tense — "add feature" not "added feature"
- Keep the first line under 72 characters
- One commit = one logical change. Don't bundle unrelated things.
- Commit often. Small commits are easier to review and revert.
- Never commit broken code to a shared branch.
- Never commit secrets (API keys, passwords). Add them to `.env` and `.gitignore`.

---

## Pull Requests

### Before opening a PR

```bash
# Bring your branch up to date with main
git fetch origin
git rebase origin/main

# Double-check your own diff before anyone else sees it
git diff main...HEAD
```

### PR title

Use the same format as commit messages:

```
feat(auth): add Google OAuth login
fix(dashboard): chart not rendering on Safari
```

### PR description (keep it simple)

```
## What does this PR do?
Adds Google OAuth so users can sign in with their Google account.

## Related issue
Closes #24

## Changes
- Added OAuth callback route
- Updated login UI with Google button
- Added env variable for Google client ID

## How to test
1. Go to /login
2. Click "Sign in with Google"
3. Complete OAuth flow
4. Should land on dashboard
```

### PR rules

- Keep PRs small — easier to review, easier to merge
- Link every PR to its issue (`Closes #42`)
- Use Draft PRs when work is still in progress
- Don't merge your own PRs in a team setting
- Get at least one approval before merging

---

## Keeping Your Branch Up to Date

```bash
# Update your feature branch with latest main (preferred — cleaner history)
git fetch origin
git rebase origin/main

# Or merge instead (creates a merge commit)
git merge origin/main
```

---

## Undoing Mistakes

```bash
# Undo last commit but keep your changes
git reset --soft HEAD~1

# Unstage a file
git restore --staged <file>

# Discard changes in a file (careful — this is permanent)
git restore <file>

# Undo a commit that's already been pushed (safe — creates a new commit)
git revert <commit-hash>

# Amend the last commit message (before pushing only)
git commit --amend -m "corrected message"
```

---

## .gitignore Essentials

```gitignore
# Never commit these
.env
.env.local
.env.*.local

# Dependencies
node_modules/
vendor/

# Build output
dist/
build/

# OS junk
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

---

## Quick Rules to Remember

1. **Pull before you push** — always start with the latest code.
2. **Branch for everything** — never work directly on `main`.
3. **Write meaningful commit messages** — your future self will thank you.
4. **Never force-push to shared branches.**
5. **Never commit secrets.**
6. **Review your own diff** before asking others to review it.
