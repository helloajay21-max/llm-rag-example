from dotenv import load_dotenv
import os
import win32com.client
import subprocess
import time

# ==============================
# Load env
# ==============================
load_dotenv(dotenv_path=r"C:\Users\ajaykuma\PyCharmMiscProject\.env")

USERNAME = os.getenv("SAP_USERNAME")
PASSWORD = os.getenv("SAP_PASSWORD")
CLIENT = os.getenv("SAP_CLIENT")
LANG = os.getenv("SAP_LANGUAGE")
SYSTEM_NAME = os.getenv("SAP_SYSTEM")

SAP_PATH = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"

AUTO_CLOSE_TIME = 120  # seconds


# ==============================
# Kill SAP if already running
# ==============================
def kill_existing_sap():
    print("🔍 Checking for existing SAP sessions...")
    os.system("taskkill /f /im saplogon.exe >nul 2>&1")
    os.system("taskkill /f /im saplgpad.exe >nul 2>&1")  # SAP GUI process
    time.sleep(2)
    print("✅ Old SAP instances closed")


# ==============================
# Main function
# ==============================
def sap_auto_login_and_close():
    try:
        # Step 1: Kill existing SAP
        kill_existing_sap()

        # Step 2: Launch SAP
        print("🚀 Launching SAP Logon...")
        subprocess.Popen(SAP_PATH)
        time.sleep(5)

        # Step 3: Connect to SAP GUI
        SapGuiAuto = win32com.client.GetObject("SAPGUI")
        application = SapGuiAuto.GetScriptingEngine

        # Step 4: Open system
        print(f"🔗 Connecting to system: {SYSTEM_NAME}")
        connection = application.OpenConnection(SYSTEM_NAME, True)
        time.sleep(3)

        session = connection.Children(0)

        # Step 5: Login
        print("🔐 Entering credentials...")
        session.findById("wnd[0]/usr/txtRSYST-MANDT").text = CLIENT
        session.findById("wnd[0]/usr/txtRSYST-BNAME").text = USERNAME
        session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = PASSWORD
        session.findById("wnd[0]/usr/txtRSYST-LANGU").text = LANG

        session.findById("wnd[0]").sendVKey(0)

        # ==============================
        # Step 6: Handle login popup
        # ==============================
        time.sleep(3)

        try:
            if session.Children.Count > 1:
                print("⚠️ Handling multiple logon popup")

                popup = session.findById("wnd[1]")

                try:
                    popup.findById("usr/radMULTI_LOGON_OPT1").select()
                except:
                    pass

                popup.findById("tbar[0]/btn[0]").press()
                print("✅ Popup handled")

        except:
            print("No login popup")

        print("✅ SAP Login Successful")

        # ==============================
        # Step 7: Wait
        # ==============================
        print(f"⏳ Waiting {AUTO_CLOSE_TIME} seconds...")
        time.sleep(AUTO_CLOSE_TIME)

        # ==============================
        # Step 8: Close session
        # ==============================
        print("🛑 Closing SAP session...")
        session.findById("wnd[0]").close()
        time.sleep(2)

        try:
            session.findById("wnd[1]/usr/btnSPOP-OPTION1").press()
            print("✅ Exit confirmed")
        except:
            pass

        # ==============================
        # Step 9: Kill SAP completely
        # ==============================
        print("🛑 Closing SAP completely...")
        kill_existing_sap()

        print("✅ SAP fully closed")

    except Exception as e:
        print(f"❌ Error: {e}")


# ==============================
# Run
# ==============================
if __name__ == "__main__":
    sap_auto_login_and_close()