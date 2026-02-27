# netpenguins.ludus_sliver

An Ansible role to build and deploy the [Sliver C2](https://sliver.sh/) framework from source, with optional systemd service integration and configuration file support. Designed for use in [Ludus](https://docs.ludus.cloud/) ranges, but works anywhere you want a fresh, up-to-date Sliver install!

---

## 🚀 Features

- Installs all build dependencies (Go, git, build tools)
- Clones the Sliver repo and builds both `sliver-server` and `sliver-client` from source
- Supports version pinning:  
  - `sliver_version: stable` → latest release tag  
  - `sliver_version: latest` → master branch  
  - Or specify any tag/branch/commit
- Installs binaries to your chosen path and symlinks to `/usr/local/bin`
- Optionally sets up a systemd service for `sliver-server`
- Supports custom Sliver config files (YAML/JSON) via the role’s `files/` directory
* Automatically generates operator configs for `root` and all users in `/home`
* Optionally installs `sliver-implant` — a Python CLI tool to generate implants and manage listeners via the Sliver API
* Optionally bootstraps a listener and a first implant automatically at deploy time

---

## 🛠️ Requirements

- Debian-based Linux (buster, bullseye, bookworm, jammy, focal, bionic)
- Ansible 2.10+
- Internet access (to fetch Sliver and dependencies)
- **~15 GB free disk space** on the filesystem used for `sliver_build_dir` (default `/opt`). The build downloads Go toolchains, Zig, and Garble for 6 platforms before compiling. `/tmp` is typically a small tmpfs and will run out of space — always use a path on the main filesystem.

---

## ⚡ Role Variables

### Sliver Core


| Variable                | Description                                                                 | Default                |
|-------------------------|-----------------------------------------------------------------------------|------------------------|
| `sliver_repo_url`                 | Sliver GitHub repo URL                                                      | `https://github.com/BishopFox/sliver.git` |
| `sliver_version`                  | Version to install: `stable`, `latest`, or any tag/branch/commit            | `stable`               |
| `sliver_install_path`             | Where to install the Sliver binaries                                        | `/usr/local/bin`       |
| `sliver_build_dir`                | Directory used to clone and build Sliver. **Avoid `/tmp`** — it is a small tmpfs. Use a path on the main filesystem (e.g. `/opt/sliver-src`). Deleted after a successful build. | `/opt/sliver-src`      |
| `sliver_min_disk_gb`              | Minimum free GB required on the `sliver_build_dir` filesystem before starting the build. The asset downloads alone (~10 GB) will fail if space is insufficient. | `15`                   |
| `sliver_build_user`               | User to build as                                                            | `root`                 |
| `sliver_create_service`           | Whether to install a systemd service for `sliver-server`                    | `true`                 |
| `sliver_service_name`             | Name of the systemd service                                                 | `sliver-server`        |
| `sliver_service_user`             | User to run the service as                                                  | `root`                 |
| `sliver_service_group`            | Group to run the service as                                                 | `root`                 |
| `sliver_service_args`             | Extra arguments for the service                                             | `""`                   |
|`sliver_generate_operator_configs` | Create operator config for root user ans users                              | `true`                 |

### Operator Config Generation

| Variable | Description | Default |
|---|---|---|
| `sliver_generate_operator_configs` | Auto-generate operator configs for root and all `/home` users | `true` |
| `sliver_root_lhost_ip` | lhost for root operator config | `localhost` |
| `sliver_users_lhost_ip` | lhost for user operator configs | `{{ ansible_default_ipv4.address }}` |

Configs are saved to:
- `/root/.sliver-client/configs/root_localhost.cfg`
- `/home/<user>/.sliver-client/configs/<user>.cfg` for each user in `/home`

### Implant Generator

| Variable | Description | Default |
|---|---|---|
| `sliver_install_implant_generator` | Install `sliver-implant` CLI tool | `true` |
| `sliver_py_repo` | sliver-py repository URL | `https://github.com/moloch--/sliver-py.git` |
| `sliver_py_branch` | sliver-py branch/tag to install | `v1.6.x` |
| `sliver_implant_venv_path` | Path for the Python venv | `/opt/sliver-py-venv` |
| `sliver_implant_script_path` | Deployment path for `sliver-implant.py` | `/opt/sliver-implant.py` |
| `sliver_implant_script_owner` | Owner of the script | `root` |

### Operator Config (for implant generator)

| Variable | Description | Default |
|---|---|---|
| `sliver_operator_name` | Operator name whose config is used by `sliver-implant` | `kali` |
| `sliver_operator_config_dir` | Directory containing the operator config | `/home/kali/.sliver-client/configs` |
| `sliver_operator_config_path` | Full path to the operator config | `{{ sliver_operator_config_dir }}/{{ sliver_operator_name }}.cfg` |

### Bootstrap Listener

| Variable | Description | Default |
|---|---|---|
| `sliver_create_listener` | Start a listener after deployment | `true` |
| `sliver_listener_c2` | C2 URL for the listener | `mtls://0.0.0.0:8888` |

### Bootstrap Implant

| Variable | Description | Default |
|---|---|---|
| `sliver_create_implant` | Generate a first implant after deployment | `true` |
| `sliver_implant_profile_name` | Sliver profile name (shown in `profiles`/`builds`) | `mtls_profile` |
| `sliver_implant_file_name` | Output filename without extension | `editor` |
| `sliver_implant_c2` | C2 callback URL (must be reachable from target) | `mtls://{{ ansible_default_ipv4.address }}:8888` |
| `sliver_implant_os` | Target OS (`windows`, `linux`, `darwin`) | `windows` |
| `sliver_implant_arch` | Target arch (`amd64`, `386`, `arm64`) | `amd64` |
| `sliver_implant_format` | Output format (`exe`, `shared`, `shellcode`, `service`) | `exe` |
| `sliver_implant_beacon` | Generate a beacon instead of a session implant | `true` |
| `sliver_implant_beacon_interval` | Beacon interval in seconds | `60` |
| `sliver_implant_beacon_jitter` | Beacon jitter percentage | `30` |
| `sliver_implant_output_dir` | Directory to save generated implant | `/opt/sliver-implants` |

> **Note:** Do not include a file extension in `sliver_implant_file_name` — the role appends `.{{ sliver_implant_format }}` automatically.
---

## 📝 Usage

### Example Ludus Role Usage

```yaml
ludus:
  - vm_name: SLIVER
    hostname: sliver
    template: debian-12-x64-server-template
    vlan: 100
    ip_last_octet: 10
    ram_gb: 2
    cpus: 2
    linux: true
    roles:
      - netpenguins.ludus_sliver
    role_vars:
      sliver_version: stable
      sliver_build_dir: /opt/sliver-src   # avoid /tmp — it is a small tmpfs
      sliver_create_service: true
      sliver_generate_operator_configs: true
      sliver_install_implant_generator: true
      sliver_operator_name: kali
      sliver_create_listener: true
      sliver_listener_c2: "mtls://0.0.0.0:8888"
      sliver_create_implant: true
      sliver_implant_c2: "mtls://10.2.100.10:8888"
      sliver_implant_profile_name: my_profile
      sliver_implant_file_name: payload
      sliver_implant_os: windows
      sliver_implant_format: exe
      sliver_implant_beacon: true
```

### Standalone Playbook Example

```yaml
- hosts: sliver
  become: yes
  roles:
    - role: netpenguins.ludus_sliver
      vars:
        sliver_version: stable
        sliver_create_service: true
        sliver_generate_operator_configs: true
        sliver_install_implant_generator: true
        sliver_operator_name: kali
        sliver_create_listener: true
        sliver_create_implant: true
        sliver_implant_c2: "mtls://192.168.1.10:8888"
```
---

## 🔄 Bootstrap Flow

When `sliver_install_implant_generator: true`, the role executes this sequence:

```
1. Check disk space on `sliver_build_dir` filesystem (need ≥ `sliver_min_disk_gb` GB)
   Build & install sliver-server + sliver-client into `sliver_install_path`
   (skipped if both binaries already exist)
2. Install systemd service (if sliver_create_service)
3. Generate operator configs (if sliver_generate_operator_configs)
       → /root/.sliver-client/configs/root_localhost.cfg
       → /home/<user>/.sliver-client/configs/<user>.cfg  (for each user)
4. Install sliver-py venv + deploy sliver-implant CLI
5. Ensure sliver-server service is started
6. Wait for multiplayer port (31337)
7. [sliver_create_listener]  Start listener
       (skipped if same protocol + port already running)
8. [sliver_create_implant]   Generate implant → {{ sliver_implant_output_dir }}/{{ sliver_implant_file_name }}.{{ sliver_implant_format }}
       (skipped if file already exists)
```

All bootstrap steps are idempotent — re-running the role will not duplicate listeners or regenerate existing implants.

---

## 🐍 Implant Generator (`sliver-implant`)

The role deploys a Python CLI tool at `/usr/local/bin/sliver-implant` backed by a dedicated venv at `{{ sliver_implant_venv_path }}`.

### Commands

```bash
# Generate a session implant (mTLS)
sliver-implant generate \
  --config ~/.sliver-client/configs/kali.cfg \
  --name my_implant \
  --c2 mtls://10.0.0.1:8888

# Generate an HTTP beacon
sliver-implant generate \
  --config ~/.sliver-client/configs/kali.cfg \
  --name http_beacon \
  --c2 http://10.0.0.1:8080 \
  --beacon --interval 30 --jitter 20 \
  --output payload.exe

# Generate a Linux shared library
sliver-implant generate \
  --config ~/.sliver-client/configs/kali.cfg \
  --name linux_lib \
  --c2 https://domain.com:443 \
  --os linux --format shared

# Start a listener (checks for duplicates automatically)
sliver-implant start-listener \
  --config ~/.sliver-client/configs/kali.cfg \
  --c2 mtls://0.0.0.0:8888

# List active listener jobs
sliver-implant list-jobs \
  --config ~/.sliver-client/configs/kali.cfg

# Kill a listener
sliver-implant kill-job \
  --config ~/.sliver-client/configs/kali.cfg --id 1

# List saved profiles
sliver-implant list-profiles \
  --config ~/.sliver-client/configs/kali.cfg

# List existing builds
sliver-implant list-builds \
  --config ~/.sliver-client/configs/kali.cfg

# Delete a profile
sliver-implant delete-profile \
  --config ~/.sliver-client/configs/kali.cfg --name old_profile
```

### Supported Protocols

| C2 URL prefix | Listener type |
|---|---|
| `mtls://` | Mutual TLS |
| `http://` | HTTP |
| `https://` | HTTPS |
| `dns://` | DNS |
| `wg://` | WireGuard |

> `start-listener` automatically checks if a listener for the same protocol and port is already running and skips creation if one exists.

---

## ⚙️ Custom Configuration Files

To use custom Sliver config files (see [Sliver config docs](https://sliver.sh/docs?name=Configuration+Files)):
1. Place your `.yaml`, `.yml`, or `.json` config files in `netpenguins.ludus_sliver/files/`
2. The role will copy them to `/root/.sliver/` on the target host with secure permissions

---

## 🖥️ Systemd Service

If `sliver_create_service` is `true`, a systemd service will be installed and enabled for `sliver-server`.  
You can customize the service template by editing `templates/sliver-server.service.j2`.


## 📝 License

MIT

---

## 👤 Author

NetPenguins

Support for bootstrap listener, implant and operator configs in february 2026 by [mojeda101](https://github.com/mojeda101).

---

## For Ludus, by NetPenguins
Happy hacking! 🐧
