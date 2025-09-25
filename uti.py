from beartype import beartype
import datetime
import os
import json

valid_mail_domains = ["@gmail.com", "@outlook.com", "@yahoo.com", "@icloud.com", "@proton.me", "@zoho.com"]

@beartype
def get_filename_from_filepath(filepath: str) -> str:
    return os.path.basename(filepath)

@beartype
def strip_extension(filename: str) -> str:
    return os.path.splitext(filename)[0]

@beartype
def is_email_valid(email: str):
    index = email.rindex("@")
    domain = ""
    for i in range(index, len(email)):
        domain += email[i]
    return True if domain in valid_mail_domains else False

@beartype
def is_phone_no_valid(phone_no: int):
    return True if len(str(phone_no)) == 10 else False

#Fetch encrypted file
@beartype
def fetch_file(file_path: str):
    try:
        with open(file_path, "rb") as file:
            header_raw, data = file.read().split(b"\n", 1)
        header = json.loads(header_raw.decode())
        return header, data
    except IsADirectoryError as e:
        print("The given is a directory: ", e)
    except PermissionError as e:
        print("Permission error: ", e)
    except IOError as e:
        print("An error occurred: ", e)

#Fetch key shares or subkeys
@beartype
def fetch_shares(shares_path: str, min_keys: int = 5):
    try:
        shares = os.listdir(shares_path)
        shares_needed = []
        temp_list_2 = []
        for i in range(0, min_keys):
            with open(shares_path + shares[i], "r") as file:
                shares_needed.append(file.readlines())
        return shares_needed
    except FileNotFoundError as e:
        print("File not found: ", e)
    except IsADirectoryError as e:
        print("Tried to read a directory as a file: ", e)
    except PermissionError as e:
        print("Permission error :", e)
    except IOError as e:
        print("An error occurred: ", e)

def watermark(account_id: str, time: str=""):
    if not time:
        time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"""\n\n\nTime: {time}
Account: {account_id}""".encode("utf-8")