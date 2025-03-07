#!/usr/bin/env python
import time
import io
from tqdm import tqdm
from typer import Typer
from pathlib import Path
import ase
import typer
from logmd import LogMD
from logmd.cli.auth import auth_app

app = Typer(name="logmd", rich_markup_mode="rich")
app.add_typer(auth_app, name="")


@app.command(name="upload")
def upload_file(
    file_path: Path = typer.Argument(help="The path to the file to upload."),
    project: str = typer.Option(
        default="", help="The project to upload to [requires login]."
    ),
):
    """
    Upload a file to LogMD.
    """
    logmd_obj = LogMD(project=project)
    content = file_path.read_text()
    model_count = content.count("MODEL")

    if model_count <= 1:
        atoms = ase.io.read(file_path)
        logmd_obj(atoms)
    else:
        models = content.split("\nMODEL")
        for model in tqdm(
            models[1:]
        ):  # Skip the first split part as it is before the first MODEL
            buffer = io.StringIO("MODEL" + model)
            # Ensure buffer content is a string
            buffer_content = buffer.getvalue()
            if isinstance(buffer_content, bytes):
                buffer_content = buffer_content.decode(
                    "utf-8"
                )  # Decode bytes to string
            atoms = ase.io.read(
                io.StringIO(buffer_content), format="proteindatabank"
            )  # Specify the correct format if needed
            logmd_obj(atoms)

            time.sleep(0.2)


@app.command(name="watch")
def watch_from_terminal(file_path: Path):
    """
    Watch a file and upload it to LogMD when it changes.
    """
    import hashlib

    hash = ""
    logmd_obj = LogMD()
    while True:
        new_hash = hashlib.sha256(open(file_path, "rb").read()).hexdigest()
        if new_hash != hash:
            print(f"found change in {file_path}, uploading...")
            hash = new_hash
            logmd_obj(ase.io.read(file_path))
        time.sleep(0.5)


@app.command(name="demos", rich_help_panel="Resources")
def demos():
    """
    Display demos.
    """
    from rich.table import Table
    import rich

    table = Table(title="Demos")
    table.add_column("What")
    table.add_column("Where")

    table.add_row(
        "[green]Login[/green]",
        "[dim]Learn how to login[/dim]\n[blue]https://github.com/log-md/logmd/blob/main/demos/demo_login.py[/blue]",
    )
    table.add_row(
        "[green]ASE[/green]",
        "[dim]See how to log with ASE[/dim]\n[blue]https://github.com/log-md/logmd/blob/main/demos/demo_ase.py[/blue]",
    )
    table.add_row(
        "[green]OpenMM[/green]",
        "[dim]See how to log with OpenMM[/dim]\n[blue]https://github.com/log-md/logmd/blob/main/demos/demo_openmm.py[/blue]",
    )

    rich.print(table)


@app.command(name="vchat", rich_help_panel="Resources")
def vchat():
    """
    Chat with LogMD.
    """
    from rich.panel import Panel
    import rich

    panel = Panel.fit(
        """
Please book a time with us here:

[blue]https://calendly.com/alexander-mathiasen/vchat[/blue]

Or reach out to us at [blue]alexmath@gmail.com[/blue]
        """,
        title="Get in touch",
        border_style="blue",
        title_align="center",
    )
    rich.print(panel)


if __name__ == "__main__":
    app()
