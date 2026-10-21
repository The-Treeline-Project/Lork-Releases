# Lork

<p align="center">
  <img src="https://github.com/The-Treeline-Project/Lork-Releases/blob/main/repository-assets/icons/lork.svg?raw=true" alt="Lork Logo" style="display:inline-block; margin:4px; width:128px; height:auto;">
</p>

---

Lork is a Pokemon Trainer Central account "tokenizer". It takes a username/password (and optionally a custom Pokemon GO OAuth2 URL) and turns that into a `refresh_token`, it exposes a API that is compatible with [Dragonite](https://github.com/UnownHash/Dragonite-Public).

Lork uses [Zendriver](https://github.com/cdpdriver/zendriver.git) and Chrome inside of a Docker container. Lork spawns a pool of browsers that it controls. It exposes the usual `/api/v1/login-code` API, but also has some more advanced routes/features, such as proxy statistics, health and more.

## Lork vs. Xilriws

Lork is a direct drop-in replacement for [Xilriws](https://github.com/UnownHash/Xilriws), so it does not lose compatibility with currently-existing tools.

Xilriws deserves a lot of credits here, Lork is more or less a fork of Xilriws that is slowly turning into a rewrite.

Lork currently has the following features that separate it with Xilriws:
- Watchdog: Lork has a built-in watchdog, that oversees browser processess and restarts/corrects them where needed.
- Multi-Instancing: Lork has built-in multi-instancing, meaning you don't need custom load-balancing/watchdog solutions.
- Efficiency: Lork is quite efficient, proxy usage is minimized as much as possible. The spawned Chrome instances are made as lightweight as possible. Lork is also generally built to be low on resource use.
- Extensive Caching: Lork downloads all the relevant web assets (JS, CSS, etc.) every 30 minutes without proxy and has one of the Lork-extension JS scripts execute a "MITM attack" on the Pokemon Trainer Central website.

Lork's core is different from Xilriw's core. Lork works like this:

1. The client sends tokenize request.
2. Lork generates a OAuth2 URL (unless it has been specified by the client).
3. Lork picks a browser from it's pool.
4. Lork obtains the tokens on-demand via that one browser.
5. Lork sends the OAuth2 token request to the Pokemon Trainer Central API.
6. Lork sends back the `refresh_token` and other relevant information back the client over the HTTP response.

While Xilriws:

1. Xilriws spawns one browser.
2. Xilriws obtains 2 cookies in advance - it constantly tries to possess two tokens.
3. The client sends a tokenize request (in case it happens before step one and two, step one and two are executed first).
4. Xilriws sends the the OAuth2 token request to the Pokemon Trainer Central API.
5. Xilriws sends back the `refresh_token` and other relevant information back the client over the HTTP response.

Lork's approach is much more efficient here, since it uses a lot less proxy bandwidth. Lork is just barely slower here, but the difference won't be more than a few seconds per tokenize request. If it is too much, you can very easily increase the amount of browsers added to the pool, so Lork will always be faster than Xilriws at a larger scale.

Lork also has a proxy manager, it has per-proxy stats saved to a `.json` file and exposes API routes. The API routes are very nicely documented using OpenAPI. 

We do not have a lot of benchmark statistics on Xilriws, but on my laptop locally with some cheap proxies I was able to get auths within ~7 seconds or so without hiccups. Obviously with cheaper proxies the success rate will be lower.

## Using Lork

Setting up Lork is a easy start-and-forget process. It requires you to install Docker on your system. Please follow the following steps to get started using Lork:

1. Copy the example config:
   ```
   cp config.yaml.example config.yaml
   ```

2. Add your proxies (one per line):
   ```
   cp proxies.txt.example proxies.txt
   ```

3. Copy the example Docker-Compose file:
   ```
   cp docker-compose.yml.example docker-compose.yml
   ```      

4. Run with Docker:
   ```
   docker compose up -d
   ```

5. Test:
   ```
   curl -X POST http://localhost:5090/api/v1/login-code \
     -H "Content-Type: application/json" \
     -d '{"username":"lork","password":"fuckyouimperva"}'
   ```

## Configuration

Edit `config.yaml` to customize:

```yaml
server:
  host: "0.0.0.0"                            # Server host IP.
  port: 5090                                 # Server host port.

browser:
  pool_size: 2                               # Number of browser instances to spawn and manage.
  headless: true                             # Wheter the browsers should be headless or not.
  health_check_interval: 30                  # Health check interval time in seconds.
  disable_gpu: false                         # Whether to disable the GPU or not. Leave false unless headless Chrome misbehaves on your host.
  disable_dev_shm: true                      # Whether to disable the dev shim or not, used for docker stuff should be yes.
  extra_args: []                             # Extra chrome arguments, leave this empty unless you know what you are doing.

auth:
  timeout: 120                               # Maximum amount of time of a single auth/tokenize request in seconds.

proxy:
  file: "proxies.txt"                        # Proxy text file that has one proxy per line; most proxy formats are accepted and auto-parsed at runtime.
  rate_limit_cooldown: 3600                  # Amount of time in seconds for a proxy to be marked dead once it has hit a rate limit.
  max_failures: 3                            # Max amount of failures before going into cooldown mode.
  flush_interval: 30                         # Interval time for when proxy stats should be written to disk.
  stats_file: "proxy_stats.json"             # File path of where the proxies should be written.
  rotate_every_uses: 1                       # Number of uses before a proxy should be rotated.
  max_uses: 0                                # Maximum uses of a proxy; leave 0 to disable.            

extensions:
  ws_port: 9091                              # First WebSocket port; each browser receives the next port.

cache:
  enabled: true                              # Cache static PTC assets locally instead of loading them through proxies.
  refresh_interval: 1800                    # Refresh cached assets directly every 30 minutes.
  dir: "/tmp/lork-asset-cache"              # Cache directory inside the Lork container.
  assets: []                                 # Additional exact URLs or paths to cache when they have no static extension.

logging:
  level: "INFO"                              # Level to log on.
  file: null                                 # File path to write logs to.
  rotation: "10 MB"                          # Log rotation after NUMBER MB.
  retention: "7 days"                        # Amount of days to keep logs for.
  colorize: true                             # Whether logs can have color or not.
  timestamps: true                           # Whether logs should include timestamps or not.
  time_format: "HH:mm:ss"                    # Format the timestamps should be displayed in.
  quiet_modules:                             # Python modules that shouldn't log anything, don't touch this unless you know what you are doing.
    - "httpx"
    - "uvicorn"
    - "zendriver"
    - "websockets"
    - "uc.connection"
  module_levels: {}                          # Per-module log levels, leave empty unless you know what you are doing.
```

All settings can be overridden with environment variables, here are some examples:

```
LORK_SERVER_PORT=5091
LORK_BROWSER_POOL_SIZE=4
LORK_PROXY_FILE=/data/proxies.txt
LORK_CACHE_ENABLED=true
LORK_CACHE_REFRESH_INTERVAL=1800
LORK_CACHE_DIR=/tmp/lork-asset-cache
```

## Proxy Formats

All of these are supported in `proxies.txt`:

```
ip:port
ip:port:username:password
ip:port@username:password
username:password@ip:port
username:password:ip:port
http://user:pass@ip:port
socks5://user:pass@ip:port
socks5h://user:pass@ip:port
LOCAL
```

Every proxy (HTTP, HTTPS, SOCKS5, SOCKS5h — with or without credentials) is routed
through an internal per-browser relay, so **authenticated SOCKS5 proxies work**
(Chromium cannot authenticate to a SOCKS5 upstream by itself). A bare `ip:port`
with no scheme is treated as HTTP; use the `socks5://` / `socks5h://` prefix for
SOCKS. Aggregate relay traffic is reported under the `relay` key of
`GET /api/v1/proxy-stats`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/login-code` | Authenticate PTC account |
| POST | `/api/v1/activate` | Activate account (stub) |
| POST | `/api/v1/cion` | Get reCAPTCHA tokens |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/proxy-stats` | View proxy statistics |

OpenAPI docs are available at `/schema/`.

## Direct Login Call

Authenticate a PTC account by calling `/api/v1/login-code` directly:

```bash
curl -X POST http://localhost:5090/api/v1/login-code \
  -H "Content-Type: application/json" \
  -d '{"username":"your-username","password":"your-password"}'
```

Successful response:

```json
{
  "login_code": "eyJhbGciOi...",
  "status": "SUCCESS"
}
```

The `url` field is optional. When omitted, Lork generates the Pokemon GO OAuth2 URL
itself. You can supply your own instead:

```bash
curl -X POST http://localhost:5090/api/v1/login-code \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password",
    "url": "https://access.pokemon.com/oauth2/auth?client_id=pokemon-go&..."
  }'
```

`status` is one of `SUCCESS`, `INVALID`, `BANNED`, `TIMEOUT` or `ERROR`, and maps to
HTTP `200`, `400`, `418`, `408` or `500` respectively.

## Updating

Lork is distributed as a pre-built Docker image, so updating is just pulling the
newest image and recreating the container:

```bash
docker compose pull
docker compose up -d
```

The image is multi-arch (`linux/amd64` and `linux/arm64`), so the correct build
for your machine is selected automatically.

## Integration with Dragonite

In your Dragonite config:

```toml
[auth.ptc]
enable = true
remote_auth_url = "http://lork:5090/api/v1/login-code"
token_refresh_only = true
#token_init_start_delay_minutes = 1
#token_init_interval_seconds = 30
#token_init_concurrency = 5
```

- `enable = true` is required for this to function. 
- `token_refresh_only = true` is strongly recommended. It means you only have to obtain the `refresh_token` once intially and Dragonite keeps it alive itself, this saves a lot of trouble and means you don't nearly have to use Lork as often.
- `token_init_start_delay_minutes` sets how many minutes Dragonite waits before it starts getting tokens. Raise it to delay the start, 
lower it to start sooner. I recommend to set this to 0/1 if you're debugging. You should leave it to the Dragonite default if not. 
- `token_init_interval_seconds` is the amount of seconds between each authentication request Dragonite sends per thread.
- `token_init_concurrency` is the amount of threads Dragonite spawns that send an auth request every `token_init_interval_seconds`. The example config I included at the top of this documentation part sends (5 * (60/30 = 2)) = 10 requests per minute.

All of these settings belong in the `[auth.ptc]` section. Leave the rest of your Dragonite config at its defaults.

Other tools should have a setting like this too.

---

Built by [The Treeline Team](https://github.com/The-Treeline-Project).

Credits go to:
- Xilriws: [UnownHash](https://github.com/UnownHash) and [Malte/ccev in specific](https://github.com/ccev) for their work on Xilriws.
- ZenDriver: [the CDPDriver project](https://github.com/cdpdriver) for their excellent work on ZenDriver.
- SVGRepo: [SVGRepo](https://www.svgrepo.com/svg/322898/open-gate) for this project's logo SVG.
