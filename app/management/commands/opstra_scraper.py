import os
import time
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Configuration
EMAIL = 'lalitpatil99799@gmail.com'
PASSWORD = 'Lalit@123'
SSO_LOGIN_URL = 'https://sso.definedge.com/auth/realms/definedge/protocol/openid-connect/auth?response_type=code&client_id=opstra&redirect_uri=https://opstra.definedge.com/ssologin&login=true&scope=openid'
CHROMEDRIVER_PATH = '/usr/local/bin/chromedriver'

# Setup WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
# options.add_argument("--headless")
options.add_argument("--disable-notifications")

service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)


def login():
    try:
        print("🌐 Logging in...")
        driver.get(SSO_LOGIN_URL)
        time.sleep(3)

        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(EMAIL)
        wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(PASSWORD)
        wait.until(EC.element_to_be_clickable((By.ID, "kc-login"))).click()
        time.sleep(5)

        driver.get("https://opstra.definedge.com/options")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        print("✅ Logged in and on options page.")
        return True
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False


def set_rows_to_all():
    try:
        print("🔧 Setting rows per page to All...")
        time.sleep(3)

        # First scroll to bottom to ensure the rows per page selector is visible
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Look for the "Rows per page:" text and click it
        rows_per_page_text = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(text(), 'Rows per page:')]"
        )))

        # Scroll the element into center view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", rows_per_page_text)
        time.sleep(1)

        # Click on the rows per page text
        driver.execute_script("arguments[0].click();", rows_per_page_text)
        print("✅ Clicked on 'Rows per page' text")
        time.sleep(2)

        # Now find and click the "All" option in the dropdown
        all_option = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class, 'v-list__tile__title') and normalize-space(text())='All']"
        )))

        # Click the "All" option
        driver.execute_script("arguments[0].click();", all_option)
        print("✅ Selected 'All' option")

        # Wait for table to update
        time.sleep(5)

        # Verify the change took effect
        table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        rows = table.find_elements(By.TAG_NAME, "tr")
        if len(rows) <= 10:  # Assuming default page size is 10
            raise Exception("Table does not show all rows after setting to 'All'")

        print(f"✅ Successfully set to show all rows. Found {len(rows)} rows.")
        return True

    except Exception as e:
        print(f"⚠️ Failed to set rows to All: {str(e)}")
        driver.save_screenshot("set_rows_error.png")
        return False


def scrape_data():
    try:
        # Try to set rows to All, retry once if failed
        if not set_rows_to_all():
            print("🔄 Retrying to set rows to All...")
            time.sleep(3)
            if not set_rows_to_all():
                print("❌ Failed to set rows to All after retry. Proceeding with visible rows only.")

        print("🔍 Extracting table data...")

        # Wait for table and scroll to ensure all data is loaded
        table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        driver.execute_script("arguments[0].scrollIntoView(true);", table)
        time.sleep(2)

        # Scroll through table to ensure all rows are loaded
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Get all rows after ensuring everything is loaded
        rows = table.find_elements(By.TAG_NAME, "tr")
        print(f"Found {len(rows)} total rows")

        data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if cols:
                data.append([col.text.strip() for col in cols])

        if not data:
            print("❌ No data found in table.")
            return

        headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, "th")]
        df = pd.DataFrame(data, columns=headers if headers and len(headers) == len(data[0]) else None)

        print(f"📊 Extracted {len(df)} rows with {len(df.columns)} columns")

        # Save to a single file with one sheet
        folder = os.path.join(os.getcwd(), "opstra_data")
        os.makedirs(folder, exist_ok=True)

        # Single file with one sheet
        filepath = os.path.join(folder, "opstra_data.xlsx")

        try:
            # Save to Excel with a single sheet, overwriting if exists
            df.to_excel(filepath, sheet_name='Options Data', index=False, engine='openpyxl')
            print(f"✅ Saved {len(df)} rows to {filepath}")

        except Exception as excel_error:
            print(f"⚠️ Excel save failed: {excel_error}")
            # Fallback to CSV
            csv_filepath = os.path.join(folder, "opstra_data.csv")
            try:
                df.to_csv(csv_filepath, index=False)
                print(f"✅ Saved data as CSV instead: {csv_filepath}")
            except Exception as csv_error:
                print(f"❌ CSV save also failed: {csv_error}")
                driver.save_screenshot("save_error.png")

    except Exception as e:
        print(f"❌ scrape_data error: {e}")
        driver.save_screenshot("scrape_error.png")


if __name__ == "__main__":
    try:
        if login():
            scrape_data()
        else:
            print("❌ Login failed. Exiting.")
    finally:
        driver.quit()