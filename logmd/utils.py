import os
import random

from logmd.constants import ADJECTIVES, NOUNS

FE_DEV = "http://localhost:5173"
FE_PROD = "https://rcsb.ai"
BE_DEV = "https://alexander-mathiasen--logmd-upload-frame-dev.modal.run"
BE_PROD = "https://alexander-mathiasen--logmd-upload-frame.modal.run"

BE_DEV_BCIF = "https://alexander-mathiasen--logmd-upload-frame-bcif-dev.modal.run"
BE_PROD_BCIF = "https://alexander-mathiasen--logmd-upload-frame-bcif.modal.run"


def is_dev():
    dev = os.environ.get("LOGMD_DEV", "false").lower() == "true"
    return dev


def get_fe_base_url():
    return FE_PROD if not is_dev() else FE_DEV


def get_upload_url():
    return BE_PROD if not is_dev() else BE_DEV

def get_upload_url_bcif():
    return BE_PROD_BCIF if not is_dev() else BE_DEV_BCIF


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


def fix_pdb_bfactor_string(pdb_content):
    # scale bfactor from [0,1] to [0,100]
    vals = []
    output_lines = []
    for line in pdb_content.splitlines():
        if line.startswith('ATOM') or line.startswith('HETATM'):
            prefix = line[:60]
            bfactor_str = line[60:66].strip()
            suffix = line[66:]
            bfactor = float(bfactor_str) 
            if bfactor <= 1.0: bfactor = int(bfactor * 100)
            vals.append(bfactor)
            new_bfactor_str = f"{bfactor}".rjust(6)[:6]
            output_lines.append(f"{prefix}{new_bfactor_str}{suffix}")
        else:
            output_lines.append(line)
    return '\n'.join(output_lines), vals

def clean_for_ASE(pdb):
    # remove additional lines, helps ASE read. 
    lines = pdb.split('\n')
    lines = [line for line in lines if line.startswith('ATOM') or line.startswith('HETATM')]
    return '\n'.join(lines)

import gemmi
from mmcif.io.IoAdapterPy import IoAdapterPy
from mmcif.api.DictionaryApi import DictionaryApi
from mmcif.io.BinaryCifWriter import BinaryCifWriter
from pathlib import Path
import gzip 
import requests
import shutil
from tqdm import tqdm 

def pdb_to_cif(pdb_path, cif_path):
    st = gemmi.read_pdb(pdb_path)
    doc = st.make_mmcif_document()
    doc.write_file(cif_path)

    # these lines break molstar. 
    with open(cif_path, "r") as f:
        content = f.read()
        loops = content.split('loop_')
        loops = loops[0] + 'loop_'+loops[-1]

    with open(cif_path, "w") as f:
        f.write(loops)

def cif_to_bcif(cif_path, bcif_path):
    mmcif_dic_path = Path.home() / 'mmcif_pdbx_v5_next.dic'
    if not mmcif_dic_path.exists():
        #url = 'https://mmcif.wwpdb.org/dictionaries/ascii/mmcif_pdbx_v5_next.dic.gz'# slow 20kb/s
        url = 'https://logmd.b-cdn.net/public/mmcif_pdbx_v5_next.dic.gz' # fast 600kb/s

        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            total_kb = total // 1024
            import io 
            buf = io.BytesIO()
            bar_fmt = '{l_bar}{bar}| {n_fmt}KB/{total_fmt}KB [{rate_fmt}]'
            with tqdm(total=total_kb, unit='KB', bar_format=bar_fmt) as pbar:
                for chunk in r.iter_content(chunk_size=8192):
                    buf.write(chunk)
                    pbar.update(len(chunk) // 1024)
            buf.seek(0)
            with gzip.open(buf, 'rb') as f_in, open(mmcif_dic_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    io = IoAdapterPy(raiseExceptions=True)
    dApi = DictionaryApi(io.readFile(inputFilePath=mmcif_dic_path), consolidate=True)
    containers = io.readFile(inputFilePath=cif_path) 
    BinaryCifWriter(dApi).serialize(bcif_path, containers)


import numpy as np 
from bitarray import bitarray
def arr_to_xbit(arr, filename, version=0):
    # arr:  interpreted as xyz array with [A] 
    # scales to 0.001 accuracy in uint and then saves with minimal number of bits. 
    a = (1000*arr).astype(np.int64).reshape(-1) 
    min = int(a.min())
    a = a - min
    bit = int(np.log2(a.max())+1) 
    c = np.vectorize(lambda x: np.binary_repr(x, width=bit))(a)
    bits = bitarray()
    bits.extend(''.join(c))
    with open(filename, 'wb') as f:
        f.write(bit.to_bytes(1, byteorder='little'))  # Store bit as 1 byte
        f.write(min.to_bytes(4, byteorder='little', signed=True))  # Store min as 4 bytes (int32)
        f.write(version.to_bytes(1, byteorder='little'))  # Store version as 1 bytes (int32)
        bits.tofile(f)