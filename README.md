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

---

## 🛠️ Requirements

- Debian-based Linux (buster, bullseye, bookworm, jammy, focal, bionic)
- Ansible 2.10+
- Internet access (to fetch Sliver and dependencies)

---

## ⚡ Role Variables

| Variable                | Description                                                                 | Default                |
|-------------------------|-----------------------------------------------------------------------------|------------------------|
| `sliver_repo_url`       | Sliver GitHub repo URL                                                      | `https://github.com/BishopFox/sliver.git` |
| `sliver_version`        | Version to install: `stable`, `latest`, or any tag/branch/commit            | `stable`               |
| `sliver_install_path`   | Where to install the Sliver binaries                                        | `/usr/local/bin`       |
| `sliver_build_user`     | User to build as                                                            | `root`                 |
| `sliver_create_service` | Whether to install a systemd service for `sliver-server`                    | `true`                 |
| `sliver_service_name`   | Name of the systemd service                                                 | `sliver-server`        |
| `sliver_service_user`   | User to run the service as                                                  | `root`                 |
| `sliver_service_group`  | Group to run the service as                                                 | `root`                 |
| `sliver_service_args`   | Extra arguments for the service                                             | `""`                   |

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
      sliver_version: stable   # or 'latest', or a specific tag/branch
      sliver_create_service: true
      sliver_service_user: root
      sliver_install_path: /opt/sliver
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
```

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

---

## For Ludus, by NetPenguins
Happy hacking! 🐧
