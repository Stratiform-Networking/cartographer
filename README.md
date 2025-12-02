# Cartographer

<iframe src="https://cartographer.artzima.dev/embed/yJLRHFuiajaxkWvLc44Gm0f4" width="100%" height="600" frameborder="0" style="border-radius: 8px;"></iframe>

**See every device on your network at a glance.**

Cartographer is a self-hosted app that maps out your home or office network. It finds all the devices, shows how they're connected, and keeps an eye on their health — so you always know what's online and what's not.

## What it does

- **Discovers your network** — Hit "Run Mapper" and watch as devices appear: routers, servers, NAS boxes, phones, smart home gadgets, you name it.
- **Drag-and-drop editing** — Rearrange the map to match how your network actually looks. Label things, group them, make it yours.
- **Health at a glance** — Green rings mean online. Red means trouble. No more guessing if your printer is down again.
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

## Tips

- **Pan mode** lets you scroll and zoom around the map.
- **Edit mode** lets you drag nodes, change their type, and rewire connections.
- Click any device to see more details and health info.
- Your changes auto-save, but you can also use **Save Map** to be sure.

## Need help?

- Make sure Docker is running and you're on the same network you want to map.
- The app needs to run with elevated network permissions to scan devices — Docker Compose handles this automatically.
- For advanced setup (production deployments, custom ports, etc.), check out `deploy.sh --help` and the compose files.

---

Built with FastAPI, Vue, and a lot of ping packets. 🗺️
