# 🗺️ Cartographer

[![Network Map](https://raw.githubusercontent.com/DevArtech/cartographer/refs/heads/main/assets/application.png)](https://cartographer.artzima.dev/embed/yJLRHFuiajaxkWvLc44Gm0f4)

> 🖱️ **[Click the image to view the interactive map](https://cartographer.artzima.dev/embed/yJLRHFuiajaxkWvLc44Gm0f4)**

**See every device on your network at a glance.**

Cartographer is a self-hosted app that maps out your home or office network. It finds all the devices, shows how they're connected, and keeps an eye on their health — so you always know what's online and what's not.

## What it does

- **Discovers your network** — Hit "Run Mapper" and watch as devices appear: routers, servers, NAS boxes, phones, smart home gadgets, you name it.
- **Drag-and-drop editing** — Rearrange the map to match how your network actually looks. Label things, group them, make it yours.
- **Health at a glance** — Green rings mean online. Red means trouble. No more guessing if your printer is down again.
- **Smart alerts** — Get notified when something goes wrong. Cartographer learns your network's normal patterns and alerts you to unusual behavior — like a device going offline unexpectedly or sudden latency spikes.
- **AI assistant** — Ask questions about your network in plain English. "What's down?" "Why is my connection slow?" Get instant answers.
- **Live updates** — See network changes in real-time as devices come online or go offline.
- **Saves your work** — Your layout is saved automatically, so you don't lose your changes.
- **Multi-user** — Set up accounts for family or teammates with different access levels.

## Getting started

You'll need [Docker](https://docs.docker.com/get-docker/) installed.

**Option 1** — Use the helper script:
```bash
./deploy.sh up
```

**Option 2** — Or run Docker Compose directly:
```bash
docker compose up --build -d
```

Then open **http://localhost:8000** in your browser.

The first time you visit, you'll create an owner account. After that, click **Run Mapper** to scan your network and start building your map!

## AI Assistant

The assistant can answer questions about your network using natural language:

- *"What devices are unhealthy?"*
- *"Show me devices with high latency"*
- *"Which devices have been offline today?"*
- *"Summarize my network health"*

To enable the assistant, you'll need to configure at least one AI provider. Copy `.example.env` to `.env` and add your API key:

```bash
cp .example.env .env
# Edit .env and add your API key (OpenAI, Anthropic, Google, or use Ollama for free local models)
```

If you run [Ollama](https://ollama.ai) locally, no API key is needed — just make sure it's running!

## Notifications

Cartographer can alert you when things go wrong on your network:

![Discord Notification](https://raw.githubusercontent.com/DevArtech/cartographer/refs/heads/main/assets/notification.png)

- **Device down** — Know immediately when a server, router, or important device stops responding.
- **Device recovered** — Get a heads-up when things come back online.
- **Unusual behavior** — Cartographer learns what's normal for your network and flags anything strange — like unexpected outages or performance issues.

### Notification channels

You can receive alerts via:

- **Email** — Get clean, easy-to-read emails when something needs your attention.
- **Discord** — Send alerts to a Discord channel or get direct messages from the Cartographer bot.

### Setting up email notifications

To receive email alerts, sign up for a free [Resend](https://resend.com) account and add your API key to `.env`:

```bash
RESEND_API_KEY=your_key_here
```

### Setting up Discord notifications

1. **Create a Discord app** — Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click "New Application". Give it a name like "Cartographer".

2. **Create a bot** — In your app's settings, go to the "Bot" section and click "Add Bot". Copy the bot token.

3. **Add your credentials to `.env`**:
   ```bash
   DISCORD_BOT_TOKEN=your_bot_token
   DISCORD_CLIENT_ID=your_client_id  # Found in the "General Information" section
   ```

4. **Invite the bot to your server** — Once Cartographer is running, go to the notification settings in the app. You'll find an invite link to add the bot to your Discord server.

5. **Pick a channel** — In the app's notification preferences, select which Discord server and channel should receive alerts (or enable DMs to get alerts privately).

### Customizing your alerts

In the app, you can configure:
- Which types of alerts you want (device offline, anomalies, etc.)
- Quiet hours so you're not woken up at 3am
- Rate limits to prevent notification spam
- Minimum priority threshold

## Configuration

All settings are optional and have sensible defaults. To customize, copy the example file:

```bash
cp .example.env .env
```

Then edit `.env` with your settings. See `.example.env` for all available options and descriptions.

## Tips

- **Pan mode** lets you scroll and zoom around the map.
- **Edit mode** lets you drag nodes, change their type, and rewire connections.
- Click any device to see more details and health info.
- Your changes auto-save, but you can also use **Save Map** to be sure.
- Open the **Assistant** panel and ask questions about your network in plain English.
- Set up **Notifications** to stay informed — the more Cartographer monitors your network, the smarter its alerts get.

## Contributing

### Commit conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for semantic versioning. All commits must follow this format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Commit types:**

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | Minor (0.x.0) |
| `fix` | Bug fix | Patch (0.0.x) |
| `perf` | Performance improvement | Patch |
| `docs` | Documentation only | None |
| `style` | Code style (formatting, semicolons) | None |
| `refactor` | Code refactoring | None |
| `test` | Adding or updating tests | None |
| `chore` | Maintenance tasks | None |
| `ci` | CI/CD changes | None |
| `build` | Build system changes | None |
| `lint` | Linting fixes | None |
| `config` | Configuration changes | None |

**Examples:**
```bash
feat(auth): add OAuth2 support
fix(network): resolve connection timeout issue
docs: update README with deployment instructions
refactor(backend): simplify database queries
```

**Breaking changes** trigger a major version bump. Add `!` after the type or include `BREAKING CHANGE:` in the footer:
```bash
feat!: redesign API endpoints
```

### Setup for development

```bash
# Install development dependencies (commit validation)
npm install

# The prepare script automatically sets up git hooks
```

### Automatic releases

Commits on the `main` branch automatically trigger a release:
1. Version is bumped based on commit type (`feat` → minor, `fix` → patch)
2. `CHANGELOG.md` is updated
3. A git tag is created

After committing, push the release:
```bash
git push --follow-tags origin main
# Or use the helper script:
npm run push:release
```

**Skip auto-release for a commit:**
```bash
SKIP_AUTO_RELEASE=1 git commit -m "chore: quick fix"
# Or use the npm script:
npm run commit:no-release
```

### Manual releases

```bash
# Preview what the next release would look like
npm run release:dry-run

# Create a release (bumps version, updates changelog, creates tag)
npm run release

# Or specify the version bump type
npm run release:patch  # 0.0.x
npm run release:minor  # 0.x.0
npm run release:major  # x.0.0
```

## Need help?

- Make sure Docker is running and you're on the same network you want to map.
- The app needs elevated network permissions to scan devices — Docker Compose handles this automatically.
- **Assistant not responding?** Make sure at least one AI provider is configured in your `.env` file.
- **Not receiving notifications?** Check that your email or Discord credentials are set up correctly in `.env`, and make sure notifications are enabled in your preferences.
- For advanced setup (production deployments, custom ports, etc.), check out `deploy.sh --help`.

---

Built with FastAPI, Vue, and a lot of ping packets. 🗺️
