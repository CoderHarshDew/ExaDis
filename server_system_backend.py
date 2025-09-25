from beartype import beartype
import datetime
import os
import hashlib
import json
import uti
from uti import strip_extension


class GlobalData:
    status = ""
    directory = "server_system/"


@beartype
def calc_hash_and_get_data(path_to_file: str):
    data_full = b""
    try:
        with open(path_to_file, "rb") as file:
            sha256 = hashlib.sha256()
            while True:
                data = file.read(4096)
                if not data:
                    break
                data_full += data
                sha256.update(data)

        return sha256.hexdigest(), data_full
    except IsADirectoryError as e:
        GlobalData.status += "The given is a directory: " + str(e) + "\n"
    except PermissionError as e:
        GlobalData.status += "Permission error: " + str(e) + "\n"
    except IOError as e:
        GlobalData.status += "An error occurred: " + str(e) + "\n"


@beartype
def sign_up(username: str, acc_id: str, ps: str, ps_confirm: str, email: str, phone_no: int):
    os.makedirs(GlobalData.directory, exist_ok=True)
    try:
        with open(GlobalData.directory + "accounts.json", "r") as file:
            accounts_data = json.load(file)

        if acc_id in accounts_data:
            raise ValueError(f"An account with id {acc_id} already exists")
        if ps != ps_confirm:
            raise ValueError("Password doesn't match with confirmed password")

        if uti.is_email_valid(email) and uti.is_phone_no_valid(phone_no):
            acc_dat = {
                "Username" : username,
                "Password": hashlib.sha256(ps.encode()).hexdigest(),  # hashed
                "Email": email,
                "Phone": phone_no,
            }
            accounts_data[acc_id] = acc_dat
            with open(GlobalData.directory + "accounts.json", "w") as file:
                json.dump(accounts_data, file, indent=4)
        else:
            raise ValueError("Incorrect Email or Phone No")
    except FileNotFoundError as e:
        GlobalData.status += "File Not Found: " + str(e)
    except IsADirectoryError as e:
        GlobalData.status += "Is a directory: " + str(e)
    except PermissionError as e:
        GlobalData.status += "Permission Error: " + str(e)
    except IOError as e:
        GlobalData.status += "IO Error: " + str(e)


@beartype
def log_in(username: str, acc_id: str, ps: str):
    os.makedirs(GlobalData.directory, exist_ok=True)
    try:
        with open(GlobalData.directory + "accounts.json", "r") as file:
            accounts_data = json.load(file)

        if acc_id not in accounts_data:
            raise ValueError("No such account exists")
        if accounts_data[acc_id]["Username"] != username:
            raise ValueError("Invalid username")

        hashed_input = hashlib.sha256(ps.encode()).hexdigest()
        return accounts_data[acc_id]["Password"] == hashed_input
    except FileNotFoundError as e:
        GlobalData.status += "File Not Found: " + str(e)
    except IsADirectoryError as e:
        GlobalData.status += "Is a directory: " + str(e)
    except PermissionError as e:
        GlobalData.status += "Permission Error: " + str(e)
    except IOError as e:
        GlobalData.status += "IO Error: " + str(e)

@beartype
def update_acc_details(username: str, ps_prev: str, acc_id: str, ps_new: str = "", email: str = "", phone_no: int = 0):
    os.makedirs(GlobalData.directory, exist_ok=True)
    try:
        with open(GlobalData.directory + "accounts.json", "r") as file:
            accounts_data = json.load(file)

        if acc_id not in accounts_data:
            raise ValueError(f"The account {acc_id} does not exist")

        if accounts_data[acc_id]["Password"] != hashlib.sha256(ps_prev.encode()).hexdigest():
            raise ValueError("Incorrect password")

        if ps_new:
            accounts_data[acc_id]["Password"] = hashlib.sha256(ps_new.encode()).hexdigest()

        if username:
            accounts_data[acc_id]["Username"] = username

        if email:
            if uti.is_email_valid(email):
                accounts_data[acc_id]["Email"] = email
            else:
                raise ValueError("Not a valid email")

        if phone_no:
            if uti.is_phone_no_valid(phone_no):
                accounts_data[acc_id]["Phone"] = phone_no
            else:
                raise ValueError("Not a valid phone number")

        with open(GlobalData.directory + "accounts.json", "w") as file:
            json.dump(accounts_data, file, indent=4)

    except Exception as e:
        GlobalData.status += f"{type(e).__name__}: {e}\n"


@beartype
def file_upload(file_data: bytes, file_name: str):
    upload_time = datetime.datetime.now()
    upload_time_fmt = upload_time.strftime("%Y%m%d_%H%M%S")
    file_dir = (
        GlobalData.directory
        + "files/"
        + strip_extension(file_name)
        + upload_time_fmt
        + "/"
    )
    os.makedirs(file_dir, exist_ok=True)  # ensure directory exists

    try:
        with open(file_dir + file_name, "wb") as file:
            file.write(file_data)
        with open(file_dir + "config.json", "w") as file:
            json.dump({}, file, indent=4)
        with open(file_dir + "file_data.json", "w") as file:
            json.dump(
                {
                    "File Name": file_name,
                    "Upload Time": upload_time.isoformat(),
                    "File Location": file_dir,
                },
                file,
                indent=4
            )
    except IsADirectoryError as e:
        GlobalData.status += "Is a directory: " + str(e)
    except PermissionError as e:
        GlobalData.status += "Permission Error: " + str(e)
    except IOError as e:
        GlobalData.status += "IO Error: " + str(e)


@beartype
def put_make_downloadable_request(file_loc: str, acc_id: str):
    if not os.path.exists(file_loc + "req.json"):
        request_dat = {
            "requester": acc_id,
            "Approved": 0,
            "Disapproved": 0,
        }
        with open(file_loc + "req.json", "w") as file:
            json.dump(request_dat, file, indent=4)


@beartype
def update_download_perms(acc_id: str, signal: bool, file_loc: str):
    try:
        with open(file_loc + "config.json", "r") as file:
            file_config = json.load(file)

        file_config[acc_id] = signal
        approved = list(file_config.values()).count(True)
        disapproved = list(file_config.values()).count(False)

        with open(file_loc + "req.json", "r") as file:
            req_dat = json.load(file)

        req_dat["Approved"] = approved
        req_dat["Disapproved"] = disapproved

        with open(file_loc + "req.json", "w") as file:
            json.dump(req_dat, file, indent=4)
        with open(file_loc + "config.json", "w") as file:
            json.dump(file_config, file, indent=4)
    except FileNotFoundError as e:
        GlobalData.status += "File Not Found: " + str(e)
    except IsADirectoryError as e:
        GlobalData.status += "Is a directory: " + str(e)
    except PermissionError as e:
        GlobalData.status += "Permission Error: " + str(e)
    except IOError as e:
        GlobalData.status += "IO Error: " + str(e)


@beartype
def is_download_allowed(file_loc: str):
    try:
        with open(file_loc + "config.json", "r") as file:
            file_config = json.load(file)
        return list(file_config.values()).count(True) > 5
    except FileNotFoundError as e:
        GlobalData.status += "File Not Found: " + str(e)
    except IsADirectoryError as e:
        GlobalData.status += "Is a directory: " + str(e)
    except PermissionError as e:
        GlobalData.status += "Permission Error: " + str(e)
    except IOError as e:
        GlobalData.status += "IO Error: " + str(e)


@beartype
def fetch_enc_file(file_loc: str, file_hash: str):
    if is_download_allowed(file_loc):
        hash_calc, file_data = calc_hash_and_get_data(file_loc)
        if hash_calc == file_hash:
            return file_data
        else:
            raise ValueError("The source File has been tampered with")
    raise PermissionError("No permission to fetch this file")
