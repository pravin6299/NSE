import os
import time
import stat
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import traceback

# Configuration
EMAIL = 'pravinmali6299@gmail.com'
PASSWORD = '6353438333'
SSO_URL = 'https://sso.definedge.com/auth/realms/definedge/protocol/openid-connect/auth?response_type=code&client_id=opstra&redirect_uri=https://opstra.definedge.com/ssologin&login=true&scope=openid'
OPTIONS_URL = 'https://opstra.definedge.com/options'


def create_date_directory():
    """Create directory structure for current date"""
    try:
        # Get current date
        current_date = datetime.now()
        year = str(current_date.year)
        month = str(current_date.month).zfill(2)
        day = str(current_date.day).zfill(2)

        # Create base directory for data
        base_dir = os.path.join(os.getcwd(), 'opstra_data')
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            print(f"Created base directory: {base_dir}")

        # Create year directory
        year_dir = os.path.join(base_dir, year)
        if not os.path.exists(year_dir):
            os.makedirs(year_dir)
            print(f"Created year directory: {year_dir}")

        # Create month directory
        month_dir = os.path.join(year_dir, month)
        if not os.path.exists(month_dir):
            os.makedirs(month_dir)
            print(f"Created month directory: {month_dir}")

        # Create day directory
        day_dir = os.path.join(month_dir, day)
        if not os.path.exists(day_dir):
            os.makedirs(day_dir)
            print(f"Created day directory: {day_dir}")

        return day_dir
    except Exception as e:
        print(f"Error creating directory structure: {str(e)}")
        return os.getcwd()


def setup_driver():
    try:
        print("🔧 Setting up Chrome driver...")
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20)  # Increased wait time for better reliability
        return driver, wait
    except Exception as e:
        print(f"❌ Failed to setup Chrome driver: {str(e)}")
        raise


def wait_for_options_page(driver, wait):
    """Wait for options page to be fully loaded"""
    try:
        print("Waiting for options page to load...")
        # Wait for table to be present
        table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        # Wait for rows to be loaded
        rows = wait.until(lambda d: len(d.find_elements(By.TAG_NAME, "tr")) > 1)
        print("✅ Options page loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Error waiting for options page: {str(e)}")
        return False


def login():
    driver = None
    try:
        driver, wait = setup_driver()

        # Go to SSO login page
        print("🌐 Navigating to SSO login page...")
        driver.get(SSO_URL)
        time.sleep(3)

        # Login
        print("Entering credentials...")
        email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        email_field.clear()
        email_field.send_keys(EMAIL)

        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.clear()
        password_field.send_keys(PASSWORD)

        print("Clicking login button...")
        login_button = wait.until(EC.element_to_be_clickable((By.ID, "kc-login")))
        login_button.click()

        # Wait for login process
        time.sleep(3)

        # Navigate to options page
        print("Navigating to options page...")
        driver.get(OPTIONS_URL)

        # Wait for options page to load
        if not wait_for_options_page(driver, wait):
            raise Exception("Failed to load options page")

        return True, driver, wait

    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        if driver:
            driver.save_screenshot("login_error.png")
        return False, None, None


def set_rows_to_all(driver, wait):
    try:
        print("🔧 Setting rows per page to All...")

        # Make sure we're on options page
        if not wait_for_options_page(driver, wait):
            print("Refreshing page...")
            driver.refresh()
            if not wait_for_options_page(driver, wait):
                raise Exception("Page not loaded properly")

        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Find and click the rows per page dropdown
        print("Looking for rows per page dropdown...")
        dropdown = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'v-select__selections')]")
        ))

        # Try different click methods
        try:
            dropdown.click()
        except:
            try:
                driver.execute_script("arguments[0].click();", dropdown)
            except:
                raise Exception("Could not click dropdown")

        time.sleep(2)

        # Find and click "All" option
        print("Clicking 'All' option...")
        all_option = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'v-list__tile__title') and text()='All']")
        ))

        try:
            all_option.click()
        except:
            driver.execute_script("arguments[0].click();", all_option)

        # Wait for table to update
        time.sleep(5)

        # Verify rows loaded
        rows = driver.find_elements(By.TAG_NAME, "tr")
        row_count = len(rows)
        print(f"Found {row_count} rows after setting to All")

        if row_count <= 10:
            raise Exception("Table does not show all rows")

        print("✅ Successfully set to show all rows")
        return True

    except Exception as e:
        print(f"⚠️ Failed to set rows to All: {str(e)}")
        if driver:
            driver.save_screenshot("rows_error.png")
        return False


def scrape_data(driver, wait):
    try:
        print("📊 Starting data extraction...")

        # Make sure table is loaded
        table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        time.sleep(2)

        # Get headers
        print("Getting headers...")
        header_cells = table.find_elements(By.TAG_NAME, "th")

        # Define default headers in case we can't get them from the table
        default_headers = [
            "Strike Price", "Call OI", "Call Change in OI", "Call Volume",
            "Call LTP", "Spot Price", "Put LTP", "Put Volume", "Put Change in OI",
            "Put OI"
        ]

        # Try to get headers from table, fall back to default if empty
        headers = [th.text.strip() for th in header_cells if th.text.strip()]
        if not headers:
            print("Using default headers as table headers were empty")
            headers = default_headers

        print(f"Using {len(headers)} columns: {headers}")

        # Get data rows
        print("Getting rows...")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
        print(f"Found {len(rows)} rows")

        # Extract data
        print("Extracting data...")
        data = []
        for index, row in enumerate(rows, 1):
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) == len(headers):
                    row_data = []
                    for col in cols:
                        value = col.text.strip()
                        if not value and any(num_word in headers[len(row_data)].lower()
                                             for num_word in ['oi', 'price', 'volume', 'ltp']):
                            value = '0'
                        row_data.append(value)
                    data.append(row_data)

                if index % 100 == 0:
                    print(f"Processed {index}/{len(rows)} rows...")

            except Exception as e:
                print(f"Warning: Error processing row {index}: {str(e)}")
                continue

        if not data:
            raise Exception("No data was extracted from the table")

        # Verify data consistency
        print("\nVerifying data consistency...")
        data_cols = len(data[0]) if data else 0
        print(f"Headers: {len(headers)} columns")
        print(f"Data: {data_cols} columns")

        if data_cols != len(headers):
            print("Column count mismatch. Adjusting headers...")
            if data_cols < len(headers):
                headers = headers[:data_cols]
            else:
                while len(headers) < data_cols:
                    headers.append(f"Column_{len(headers) + 1}")

        # Create DataFrame
        print("\nCreating Excel file...")
        df = pd.DataFrame(data, columns=headers)

        # Create directory structure and get save path
        save_dir = create_date_directory()

        # Create filename with timestamp
        current_time = datetime.now().strftime("%H%M%S")
        filename = f"opstra_data_{current_time}.xlsx"
        full_path = os.path.join(save_dir, filename)

        # Save with index=False to not include row numbers
        df.to_excel(full_path, index=False)

        print(f"\n✅ Successfully saved {len(df)} rows")
        print(f"📁 File saved at: {full_path}")
        print("\nFirst few rows of saved data:")
        print(df.head())
        print(f"\nTotal rows: {len(df)}")
        print(f"Total columns: {len(df.columns)}")

        return True

    except Exception as e:
        print(f"❌ Data extraction error: {str(e)}")
        traceback.print_exc()
        if driver:
            driver.save_screenshot("scrape_error.png")
        return False


if __name__ == "__main__":
    driver = None
    try:
        print("Starting Opstra data scraper...")
        success, driver, wait = login()

        if success and driver and wait:
            print("\nStep 1: Login successful ✅")

            if set_rows_to_all(driver, wait):
                print("\nStep 2: Set rows to All successful ✅")

                if scrape_data(driver, wait):
                    print("\nStep 3: Data extraction successful ✅")
                    print("\n✨ Script completed successfully!")
                else:
                    print("\n❌ Step 3 failed: Data extraction failed")
            else:
                print("\n❌ Step 2 failed: Could not set rows to All")
        else:
            print("\n❌ Step 1 failed: Login failed")

    except Exception as e:
        print(f"\n❌ Script error: {str(e)}")

    finally:
        if driver:
            print("\nClosing browser...")
            driver.quit()