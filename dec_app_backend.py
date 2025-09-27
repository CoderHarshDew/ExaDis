from itertools import chain
from shamir_mnemonic import combine_mnemonics
import datetime
from cryptography.fernet import Fernet
import os
import json
from beartype import beartype

import uti
from uti import get_filename_from_filepath, strip_extension

class GlobalData:
    status = ""

#Reconstruct the key
@beartype
def reconstruct_key(shares: list):
    return combine_mnemonics(shares)

#Decrypt the encrypted file's data and write to a separate file
@beartype
def decrypt_file(dec_file_path: str, key: bytes, data: bytes, time: str):
    key_str = Fernet(key)
    decrypted_data = key_str.decrypt(data) + uti.watermark("acc", time)
    try:
        with open(dec_file_path, "wb") as f:
            f.write(decrypted_data)
    except IsADirectoryError as e:
        GlobalData.status = "The given is a directory: " +  str(e)
    except PermissionError as e:
        GlobalData.status = "Permission error: " + str(e)
    except IOError as e:
        GlobalData.status = "TAn error occurred: " + str(e)

@beartype
def logger(log: str):
    try:
        f_count = len(os.listdir(log))
        return "Entry " + str(f_count + 1) + ".log"
    except PermissionError as e:
        GlobalData.status = "Permission error: " + str(e)
    except IOError as e:
        GlobalData.status = "TAn error occurred: " + str(e)

#Log operation details
@beartype
def log_operations(filename: str, time: str, log_path: str):
    try:
        with open(log_path, "w") as file:
            file.write("File Name: " + filename)
            file.write("Operation Time: " + time)
    except IsADirectoryError as e:
        GlobalData.status = "The given is a directory: " +  str(e)
    except PermissionError as e:
        GlobalData.status = "Permission error: " + str(e)
    except IOError as e:
        GlobalData.status = "TAn error occurred: " + str(e)

@beartype
def start_decryption(enc_file_content: bytes, file_path: str, file_metadata: dict, sub_keys: list):

    opr_time = datetime.datetime.now()
    opr_time_fmt = opr_time.strftime("%Y%m%d_%H%M%S")

    #log location
    log = "dec/log/"
    os.makedirs(log, exist_ok=True)
    log_file = logger(log)
    log_file_path = log + log_file

    #Details of encrypted file
    enc_file_name = get_filename_from_filepath(file_path)

    #Details for making decrypted file
    dec_file_name = enc_file_name
    dec_file_dir = "dec/ops/dec_files/" + strip_extension(dec_file_name) + "_" + opr_time_fmt + "/"
    os.makedirs(dec_file_dir, exist_ok=True)
    dec_file_path = dec_file_dir + dec_file_name



    #The data in the encrypted file

    #Get required amount of shares needed for reconstruction
    min_keys = file_metadata["min_keys"]
    key = reconstruct_key(sub_keys)

    #Decrypt
    decrypt_file(dec_file_path, key, enc_file_content, opr_time_fmt)

    #Log everything
    log_operations(enc_file_name, str(opr_time), log_file_path)


if __name__ == "__main__":
    pass
