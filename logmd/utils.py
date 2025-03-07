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
