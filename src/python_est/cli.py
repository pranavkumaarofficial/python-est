"""
CLI Interface for Python-EST Server

Command-line interface for managing EST server operations.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .config import ESTConfig
from .server import ESTServer
from .auth import SRPAuthenticator
from .utils import setup_logging, create_directories, validate_certificate_files, generate_self_signed_cert

console = Console()


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.pass_context
def main(ctx: click.Context, debug: bool) -> None:
    """Python-EST: Professional EST Protocol Server"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    setup_logging(debug=debug)


@main.command()
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              default='config.yaml', help='Configuration file')
@click.pass_context
def start(ctx: click.Context, config: Path) -> None:
    """Start the EST server"""

    console.print(Panel.fit(
        "[bold blue]🚀 Python-EST Server[/bold blue]\n"
        "[cyan]Professional RFC 7030 EST Protocol Implementation[/cyan]",
        border_style="blue"
    ))

    try:
        # Load configuration
        if not config.exists():
            console.print(f"[red]Configuration file not found: {config}[/red]")
            console.print("Run 'python-est init' to create a sample configuration")
            sys.exit(1)

        est_config = ESTConfig.from_file(config)

        # Validate certificate files
        if not validate_certificate_files(
            est_config.tls.cert_file,
            est_config.tls.key_file,
            est_config.ca.ca_cert
        ):
            console.print("[red]Certificate validation failed[/red]")
            sys.exit(1)

        # Create server
        server = ESTServer(est_config)

        # Display server info
        table = Table(title="EST Server Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Host", est_config.server.host)
        table.add_row("Port", str(est_config.server.port))
        table.add_row("TLS Certificate", str(est_config.tls.cert_file))
        table.add_row("CA Certificate", str(est_config.ca.ca_cert))
        table.add_row("SRP Database", str(est_config.srp.user_db))
        table.add_row("Bootstrap Enabled", "✅" if est_config.bootstrap_enabled else "❌")

        console.print(table)

        # Start server
        console.print(f"\n[green]Starting EST server on https://{est_config.server.host}:{est_config.server.port}[/green]")
        console.print("[yellow]Press Ctrl+C to stop[/yellow]")

        asyncio.run(server.start())

    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Server error: {e}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()
        sys.exit(1)


@main.command()
@click.option('--host', default='0.0.0.0', help='Server host')
@click.option('--port', default=8443, help='Server port')
@click.option('--cert-dir', type=click.Path(path_type=Path), default=Path('certs'),
              help='Certificate directory')
def init(host: str, port: int, cert_dir: Path) -> None:
    """Initialize EST server configuration"""

    console.print(Panel.fit(
        "[bold green]🔧 EST Server Initialization[/bold green]\n"
        "[cyan]Setting up your EST server environment[/cyan]",
        border_style="green"
    ))

    # Create directories
    create_directories({})
    cert_dir.mkdir(parents=True, exist_ok=True)

    # Certificate file paths
    server_cert = cert_dir / "server.crt"
    server_key = cert_dir / "server.key"
    ca_cert = cert_dir / "ca.crt"
    ca_key = cert_dir / "ca.key"

    # Generate self-signed certificates for development
    if not server_cert.exists() or not server_key.exists():
        console.print("[yellow]Generating self-signed server certificate...[/yellow]")
        if generate_self_signed_cert(server_cert, server_key, "localhost"):
            console.print("[green]✅ Server certificate generated[/green]")
        else:
            console.print("[red]❌ Failed to generate server certificate[/red]")
            sys.exit(1)

    if not ca_cert.exists() or not ca_key.exists():
        console.print("[yellow]Generating self-signed CA certificate...[/yellow]")
        if generate_self_signed_cert(ca_cert, ca_key, "EST-CA"):
            console.print("[green]✅ CA certificate generated[/green]")
        else:
            console.print("[red]❌ Failed to generate CA certificate[/red]")
            sys.exit(1)

    # Create default configuration
    config = ESTConfig.create_default(
        cert_file=server_cert,
        key_file=server_key,
        ca_cert=ca_cert,
        ca_key=ca_key
    )

    config.server.host = host
    config.server.port = port

    # Save configuration
    config_file = Path("config.yaml")
    config.to_file(config_file)

    # Display summary
    table = Table(title="EST Server Initialized")
    table.add_column("Component", style="cyan")
    table.add_column("Path", style="magenta")

    table.add_row("Configuration", str(config_file))
    table.add_row("Server Certificate", str(server_cert))
    table.add_row("Server Key", str(server_key))
    table.add_row("CA Certificate", str(ca_cert))
    table.add_row("CA Key", str(ca_key))
    table.add_row("SRP Database", str(config.srp.user_db))

    console.print(table)

    console.print(f"\n[green]✅ EST server initialized successfully![/green]")
    console.print(f"[yellow]Next steps:[/yellow]")
    console.print("1. Add SRP users: [cyan]python-est user add <username>[/cyan]")
    console.print("2. Start server: [cyan]python-est start[/cyan]")


@main.group()
def user() -> None:
    """Manage SRP users"""
    pass


@user.command('add')
@click.argument('username')
@click.option('--password', prompt=True, hide_input=True, help='User password')
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              default='config.yaml', help='Configuration file')
def add_user(username: str, password: str, config: Path) -> None:
    """Add SRP user"""

    try:
        # Load configuration
        est_config = ESTConfig.from_file(config)
        auth = SRPAuthenticator(est_config.srp)

        # Add user
        result = asyncio.run(auth.add_user(username, password))

        if result:
            console.print(f"[green]✅ Added SRP user: {username}[/green]")
        else:
            console.print(f"[red]❌ Failed to add user: {username}[/red]")

    except Exception as e:
        console.print(f"[red]Error adding user: {e}[/red]")


@user.command('remove')
@click.argument('username')
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              default='config.yaml', help='Configuration file')
def remove_user(username: str, config: Path) -> None:
    """Remove SRP user"""

    try:
        # Load configuration
        est_config = ESTConfig.from_file(config)
        auth = SRPAuthenticator(est_config.srp)

        # Confirm removal
        if click.confirm(f"Remove user '{username}'?"):
            result = asyncio.run(auth.remove_user(username))

            if result:
                console.print(f"[green]✅ Removed SRP user: {username}[/green]")
            else:
                console.print(f"[red]❌ Failed to remove user: {username}[/red]")

    except Exception as e:
        console.print(f"[red]Error removing user: {e}[/red]")


@user.command('list')
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              default='config.yaml', help='Configuration file')
def list_users(config: Path) -> None:
    """List SRP users"""

    try:
        # Load configuration
        est_config = ESTConfig.from_file(config)
        auth = SRPAuthenticator(est_config.srp)

        # List users
        users = asyncio.run(auth.list_users())

        if users:
            table = Table(title="SRP Users")
            table.add_column("Username", style="cyan")
            table.add_column("Status", style="green")

            for username in users:
                table.add_row(username, "Active")

            console.print(table)
        else:
            console.print("[yellow]No SRP users found[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing users: {e}[/red]")


@main.command()
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              default='config.yaml', help='Configuration file')
def status(config: Path) -> None:
    """Show server status and configuration"""

    try:
        # Load configuration
        est_config = ESTConfig.from_file(config)

        # Server info
        table = Table(title="EST Server Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Status", style="green")

        # Check certificate files
        cert_status = "✅" if est_config.tls.cert_file.exists() else "❌"
        key_status = "✅" if est_config.tls.key_file.exists() else "❌"
        ca_status = "✅" if est_config.ca.ca_cert.exists() else "❌"

        table.add_row("Host", est_config.server.host, "")
        table.add_row("Port", str(est_config.server.port), "")
        table.add_row("TLS Certificate", str(est_config.tls.cert_file), cert_status)
        table.add_row("TLS Key", str(est_config.tls.key_file), key_status)
        table.add_row("CA Certificate", str(est_config.ca.ca_cert), ca_status)
        table.add_row("Bootstrap", "Enabled" if est_config.bootstrap_enabled else "Disabled",
                     "✅" if est_config.bootstrap_enabled else "❌")

        console.print(table)

        # SRP users
        auth = SRPAuthenticator(est_config.srp)
        users = asyncio.run(auth.list_users())
        console.print(f"\n[cyan]SRP Users:[/cyan] {len(users)} configured")

    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")


if __name__ == '__main__':
    main()