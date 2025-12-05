# Contributing to Cartographer

Thank you for your interest in contributing to Cartographer! This document outlines the conventions and guidelines for contributing to this project.

## Commit Message Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/) to automate version management and changelog generation. All commits must follow this format.

### Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### Type

The type must be one of the following:

| Type | Description | SemVer Impact |
|------|-------------|---------------|
| **feat** | A new feature | Minor bump (0.X.0) |
| **fix** | A bug fix | Patch bump (0.0.X) |
| **perf** | A performance improvement | Patch bump |
| **docs** | Documentation only changes | No release |
| **style** | Code style changes (formatting, semicolons, etc.) | No release |
| **refactor** | Code refactoring (no feature change or bug fix) | No release |
| **test** | Adding or updating tests | No release |
| **chore** | Maintenance tasks, dependency updates | No release |
| **ci** | CI/CD configuration changes | No release |
| **build** | Build system or external dependency changes | No release |
| **revert** | Reverting a previous commit | Depends on reverted commit |
| **lint** | Linting fixes | No release |
| **config** | Configuration file changes | No release |
| **wip** | Work in progress (should be squashed before merge) | No release |

### Scope (optional)

The scope should be the name of the affected module or service:

- `frontend` - Vue.js frontend application
- `backend` - FastAPI gateway service
- `auth` - Authentication service
- `health` - Health monitoring service
- `metrics` - Metrics collection service
- `notifications` - Notification service
- `assistant` - AI assistant service
- `network` - Network discovery functionality
- `docker` - Docker/deployment configuration

### Subject

The subject is a short description of the change:

- Use the imperative, present tense: "add" not "added" nor "adds"
- Don't capitalize the first letter
- No period (.) at the end
- Maximum 72 characters

### Body (optional)

The body should include the motivation for the change and contrast this with previous behavior.

### Footer (optional)

The footer should contain any information about **Breaking Changes** and is also the place to reference GitHub issues that this commit closes.

**Breaking Changes** should start with the word `BREAKING CHANGE:` with a space or two newlines. The rest of the commit message is then used for this.

### Examples

**Feature:**
```
feat(auth): add OAuth2 login support

Add Google and GitHub OAuth2 providers for user authentication.
Users can now log in with their existing accounts instead of
creating new credentials.

Closes #123
```

**Bug Fix:**
```
fix(network): resolve connection timeout on large networks

Increase the default timeout from 5s to 30s for network scans
with more than 254 hosts.

Fixes #456
```

**Breaking Change:**
```
feat(api)!: redesign REST API endpoints

BREAKING CHANGE: All API endpoints now use /api/v2 prefix.
The old /api/v1 endpoints are no longer available.

Migration guide:
- Update all API calls to use the new prefix
- See docs/migration-v2.md for detailed changes
```

**Simple Documentation:**
```
docs: update installation instructions for Windows
```

**Chore:**
```
chore(deps): upgrade Vue to 3.5.0
```

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/devartech/cartographer.git
   cd cartographer
   ```

2. Install development dependencies:
   ```bash
   npm install
   ```

   This will:
   - Install commitlint for commit message validation
   - Install husky for git hooks
   - Set up the commit-msg hook to validate commits

3. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat(frontend): add dark mode toggle"
   ```

   If your commit message doesn't follow the convention, the commit will be rejected with an error message explaining what's wrong.

4. **Alternative:** Use the interactive commit helper:
   ```bash
   npm run commit
   ```

   This launches an interactive prompt that guides you through creating a properly formatted commit message.

## Automatic Releases

**On the `main` branch**, a release is automatically created after each commit:
- Version is bumped based on commit type (`feat` → minor, `fix` → patch)
- `CHANGELOG.md` is updated with your changes
- A git tag is created

After committing on main, push the release:
```bash
git push --follow-tags origin main
# Or use: npm run push:release
```

### Skip Auto-Release

If you need to make a commit without triggering a release:
```bash
# Option 1: Environment variable
SKIP_AUTO_RELEASE=1 git commit -m "chore: quick fix"

# Option 2: npm script
npm run commit:no-release
```

Release commits (those starting with `chore(release):`) automatically skip the auto-release to prevent infinite loops.

## Manual Releases

Releases can also be created manually using [standard-version](https://github.com/conventional-changelog/standard-version).

```bash
# Preview what the next release would look like
npm run release:dry-run

# Create a release (auto-determines version from commits)
npm run release

# Force a specific version bump
npm run release:patch  # 0.0.X
npm run release:minor  # 0.X.0
npm run release:major  # X.0.0
```

This will:
1. Analyze commits since the last release
2. Bump the version based on commit types
3. Update the CHANGELOG.md
4. Create a git commit and tag
5. Update version in package.json and VERSION file

## Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-new-feature
   ```

2. Make your changes with proper commits

3. Push your branch and create a Pull Request

4. Ensure all CI checks pass

5. Request review from maintainers

## Questions?

If you have questions about these guidelines, feel free to open an issue or discussion.

