import subprocess
import time

def is_chrome_running():
    """Check if Chrome is running."""
    try:
        result = subprocess.run(["tasklist"], capture_output=True, text=True)
        return "chrome.exe" in result.stdout.lower()
    except Exception as e:
        print(f"Error checking Chrome process: {e}")
        return False

def kill_chrome():
    """Kill all Chrome instances."""
    try:
        subprocess.run(["taskkill", "/IM", "chrome.exe", "/F"], capture_output=True, text=True)
        print("Killed all running Chrome instances.")
    except Exception as e:
        print(f"Error killing Chrome process: {e}")

def ensure_pychrome_running():
    """Ensure Chrome is running with remote debugging enabled."""
    
    # Check if Chrome is running and kill it if necessary
    if is_chrome_running():
        print("Chrome is already running. Terminating existing instances...")
        kill_chrome()
        time.sleep(2)  # Give some time for Chrome to close
    
    # Define Chrome launch command
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = r"C:\Users\Korisnik\AppData\Local\Google\Chrome\User Data"
    profile_name = "Profile 1"

    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_name}",
        "--disable-gpu",
        "--disable-popup-blocking",
        "--disable-extensions",
        "--disable-sync",
        "--disable-translate",
        "--disable-notifications",
        "--mute-audio"
    ]

    # Launch Chrome
    try:
        subprocess.Popen(cmd)
        print("Chrome launched successfully with debugging enabled.")
    except Exception as e:
        print(f"Error launching Chrome: {e}")

# Run the function
ensure_pychrome_running()
