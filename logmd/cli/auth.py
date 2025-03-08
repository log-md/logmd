from typer import Typer
import rich
from logmd.constants import TOKEN_PATH, LOGMD_PREFIX
from logmd.auth import setup_token


auth_app = Typer(
    name="auth",
    help="Manage your LogMD token",
    rich_markup_mode="rich",
)


@auth_app.command(epilog="this is the [green]epilog[/green]")
def login():
    """
    Login to LogMD, get a token, and save it in your home directory.
    """
    setup_token()


@auth_app.command()
def logout():
    """
    Logout of LogMD by deleting the token from your home directory.
    """
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        rich.print(f"{LOGMD_PREFIX} [white]Logged out successfully[/white]")
    else:
        rich.print(f"{LOGMD_PREFIX} [red]No token found[/red]")
