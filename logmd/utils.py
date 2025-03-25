import os
import random

from logmd.constants import ADJECTIVES, NOUNS

FE_DEV = "http://localhost:5173"
FE_PROD = "https://rcsb.ai"
BE_DEV = "https://alexander-mathiasen--logmd-upload-frame-dev.modal.run"
BE_PROD = "https://alexander-mathiasen--logmd-upload-frame.modal.run"


def is_dev():
    return os.environ.get("LOGMD_DEV", "false").lower() == "true"


def get_fe_base_url():
    return FE_PROD if not is_dev() else FE_DEV


def get_upload_url():
    return BE_PROD if not is_dev() else BE_DEV


def get_run_id(num: int) -> str:
    """
    Get a run id for the given number.

    Args:
        num: The number of the project.

    Returns:
        A run id in the format of "<adjective>-<noun>-<number>".
    """
    adj, noun = (
        random.sample(ADJECTIVES, 1)[0],
        random.sample(NOUNS, 1)[0],
    )
    return f"{adj}-{noun}-{num}"


def update_pdb_positions(pdb_string, new_positions):
    """
    Replace atomic coordinates in a PDB string while retaining all metadata.

    :param pdb_string: Original PDB file content as a string.
    :param new_positions: Nx3 NumPy array of new atomic positions.
    :return: Updated PDB string.
    """
    pdb_lines = pdb_string.splitlines()
    updated_lines = []
    pos_index = 0

    for line in pdb_lines:
        if line.startswith("ATOM") or line.startswith("HETATM"):
            # Format new positions while keeping original formatting
            x, y, z = new_positions[pos_index]
            new_coords = f"{x:8.3f}{y:8.3f}{z:8.3f}"
            updated_line = f"{line[:30]}{new_coords}{line[54:]}"
            updated_lines.append(updated_line)
            pos_index += 1
        else:
            updated_lines.append(line)

    return "\n".join(updated_lines)