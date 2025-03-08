import rich
import typer

from logmd.constants import LOGMD_PREFIX, TOKEN_PATH
from logmd.data_models import LogMDToken
from logmd.utils import get_fe_base_url

from pydantic import ValidationError
from rich.prompt import Prompt


def setup_token() -> None:
    rich.print(
        f"{LOGMD_PREFIX}[white]Login here: [cyan]{get_fe_base_url()}/auth[/cyan]"
    )
    token = Prompt.ask(f"{LOGMD_PREFIX}[white]Enter your token[/white]")

    try:
        token_obj = LogMDToken.model_validate_json(token)
    except ValidationError:
        rich.print(f"{LOGMD_PREFIX}[red]Invalid token[/red]")
        raise typer.Abort()

    TOKEN_PATH.write_text(token_obj.model_dump_json())
    rich.print(f"{LOGMD_PREFIX}[green]Logged in successfully ✅[/green]")


def load_token() -> LogMDToken | None:
    if not TOKEN_PATH.is_file():
        setup_token()

    try:
        return LogMDToken.model_validate_json(TOKEN_PATH.read_text())
    except Exception:
        rich.print(
            f"{LOGMD_PREFIX}[red]token file seems corrupted, please login again[/red]"
        )
        if TOKEN_PATH.is_file():
            TOKEN_PATH.unlink()
        setup_token()
        return load_token()
