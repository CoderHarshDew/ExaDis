#Imports
import os
import datetime
from cryptography.fernet import Fernet
from shamir_mnemonic import generate_mnemonics
import hashlib
import json
from beartype import beartype
from uti import get_filename_from_filepath, strip_extension

class GlobalData:
    status = ""


#Calculate the hash of the encrypted file
@beartype
def calc_hash(path_to_enc_file: str):
    try:
        # open the file in read bytes mode
        with open(path_to_enc_file, "rb") as file:

            # initialize the SHA256 hash
            sha256 = hashlib.sha256()

            # An infinite loop to keep calculating the SHA256 hash
            while True:

                # Read file in a size of 4 byte
                data = file.read(4096)

                # validate if data exists, or if anything was left in file to read
                if not data:
                    break

                # Update SHA256 hash
                sha256.update(data)

        # return the SHA256 of the file
        return sha256.hexdigest()
    except IsADirectoryError as e:
        GlobalData.status += "The given is a directory: " + str(e) + "\n"
    except PermissionError as e:
        GlobalData.status += "Permission error: " + str(e) + "\n"
    except IOError as e:
        GlobalData.status += "An error occurred: " + str(e) + "\n"

#Log the details of this operation
@beartype
def log_operation(opr_time: str, path_to_enc_file: str, total_keys: int, min_keys: int, path_to_keys: str, enc_file_hash: str, path_to_log: str, og_file_name: str, config: dict):
    try:
        with open(path_to_log, "w") as file:
            file.write("Original File Name: " + og_file_name + "\n")
            file.write("Total Keys: " + str(total_keys) + "\n" if bool(config["log_key_count"]) else "")
            file.write("Minimum Keys for decryption: " + str(min_keys) + "\n" if bool(config["log_min_required_keys"]) else "")
            file.write("Keys location: " + path_to_keys + "\n" if bool(config["log_key_location"]) else "")
            file.write("Encrypted file location: " + path_to_enc_file + "\n" if bool(config["enc_file_location"]) else "")
            file.write("Encrypted File Hash: " + enc_file_hash + "\n" if bool(config["log_enc_file_hash"]) else "")
            file.write("Time Stamp: " + opr_time + "\n" if bool(config["log_operation_time"]) else "")
        return None
    except IsADirectoryError as e:
        GlobalData.status += "The given is a directory: " + str(e) + "\n"
    except PermissionError as e:
        GlobalData.status += "Permission error: " + str(e) + "\n"
    except IOError as e:
        GlobalData.status += "An error occurred: " + str(e) + "\n"

#Generate Key and split into parts
@beartype
def gen_keys(total_keys: int=10, min_keys: int=5):
    key = Fernet.generate_key()
    if total_keys >= min_keys:
        mnemonics = generate_mnemonics(
            group_threshold=1,  # number of groups required to reconstruct
            groups=[(min_keys, total_keys)],  # threshold=3 out of total=5 shares per group
            master_secret=key
        )
    else:
        raise ValueError("total_keys must be >= min_keys")
    return mnemonics, key

#Save the parts of the key into separate files
@beartype
def save_keys(mnemonics: list[list[str]], location: str):
    group = mnemonics[0]
    os.makedirs(location, exist_ok=True)
    for i, share in enumerate(group, 1):
        try:
            with open(os.path.join(location, f"share{i}.key"), "w") as f:
                f.write(share)
        except IsADirectoryError as e:
            GlobalData.status += "The given is a directory: " + str(e) + "\n"
        except PermissionError as e:
            GlobalData.status += "Permission error: " + str(e) + "\n"
        except IOError as e:
            GlobalData.status += "An error occurred: " + str(e) + "\n"

#Encrypt the file
@beartype
def encrypt_file(data: bytes, key: bytes, filename: str, total_keys: int, min_keys: int):
    fernet_temp = Fernet(key)
    encrypted_data = fernet_temp.encrypt(data)
    header = {
        "min_keys" : min_keys,
        "total_keys" : total_keys,
    }
    try:
        with open(filename, "wb") as f:
            f.write(json.dumps(header).encode() + b"\n" + encrypted_data)
    except IsADirectoryError as e:
        GlobalData.status += "The given is a directory: " + str(e) + "\n"
    except PermissionError as e:
        GlobalData.status += "Permission error: " + str(e) + "\n"
    except IOError as e:
        GlobalData.status += "An error occurred: " + str(e) + "\n"

@beartype
def logger(log: str):
    try:
        f_count = len(os.listdir(log))
        return "Entry " + str(f_count + 1)
    except PermissionError as e:
        GlobalData.status += "Permission error: " + str(e) + "\n"
    except IOError as e:
        GlobalData.status += "An error occurred: " + str(e) + "\n"

@beartype
def start_encryption(file_content: bytes, file_path: str):
    opr_time = datetime.datetime.now()
    opr_time_fmt = opr_time.strftime("%Y%m%d_%H%M%S")

    try:
        with open("enc/config.json") as file:
            config = json.load(file)
    except FileNotFoundError as e:
        GlobalData.status += "File Not Found: " + str(e) + "\n"
    except IsADirectoryError as e:
        GlobalData.status += "The given is a directory: " + str(e) + "\n"
    except PermissionError as e:
        GlobalData.status += "Permission error: " + str(e) + "\n"
    except IOError as e:
        GlobalData.status += "An error occurred: " + str(e) + "\n"

    #Variables
    log_location = config["log_location"]
    os.makedirs(log_location, exist_ok=True)
    log_file = logger(log_location) + ".log"
    log_file_path = log_location + log_file
    filename = get_filename_from_filepath(file_path)
    enc_file_location = config["enc_file_location"]
    enc_file_path = enc_file_location + strip_extension(filename) + "_" + opr_time_fmt + "/"
    os.makedirs(enc_file_path, exist_ok=True)
    enc_file_path += filename
    total_keys = config["total_keys"]
    min_keys = config["min_keys"]
    path_keys = enc_file_location + strip_extension(filename) + "_" + opr_time_fmt  + "/keys/"
    os.makedirs(path_keys, exist_ok=True)
    file_data = file_content

    #Key creation
    mnemonics, key_main = gen_keys(total_keys, min_keys)

    #Key saving
    save_keys(mnemonics, path_keys)

    #Encrypt file
    encrypt_file(file_data, key_main, enc_file_path, total_keys, min_keys)

    #Get hash of encrypted file
    enc_hash = calc_hash(enc_file_path)

    #Log operation
    log_operation(str(opr_time), enc_file_path, total_keys, min_keys, path_keys, enc_hash, log_file_path, filename, config)

if __name__ == "__main__":
    pass