# fetch_data.py

import os
import pandas as pd

BASE_DOWNLOAD_PATH = r"C:\Download"
os.makedirs(BASE_DOWNLOAD_PATH, exist_ok=True)

LATEST_FILE = os.path.join(BASE_DOWNLOAD_PATH, "latest_data.csv")


def fetch_latest_attachment():
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()

    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox = outlook.GetDefaultFolder(6)
    messages = inbox.Items
    messages.Sort("[ReceivedTime]", True)

    valid_extensions = (".xlsx", ".xls", ".csv")

    for message in messages:
        try:
            if "attachment" in message.Subject.lower():

                if message.Attachments.Count > 0:
                    for i in range(1, message.Attachments.Count + 1):
                        attachment = message.Attachments.Item(i)

                        print("Checking:", attachment.FileName)

                        if attachment.FileName.lower().endswith(valid_extensions):
                            file_path = os.path.join(BASE_DOWNLOAD_PATH, attachment.FileName)
                            attachment.SaveAsFile(file_path)

                            print("✅ Downloaded:", file_path)

                            pythoncom.CoUninitialize()
                            return file_path

        except Exception as e:
            print("Error:", e)

    pythoncom.CoUninitialize()
    return None


def process_data():
    file_path = fetch_latest_attachment()

    if not file_path:
        print("❌ No valid file found")
        return

    # ✅ Read downloaded file (NOT latest_data.csv)
    if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)

    if df.empty:
        print("⚠️ File is empty")
        return

    # ✅ Save final CSV
    df.to_csv(LATEST_FILE, index=False)
    print("✅ Saved:", LATEST_FILE)


if __name__ == "__main__":
    process_data()