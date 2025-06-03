from django.core.management.base import BaseCommand
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import urllib.parse
from app.models import KiteToken

# ✅ Your provided credentials
API_KEY = "doieti8s40hlpp6l"
API_SECRET = "ijm22wvh5ks2k8m1c72psg17drfj4s29"
USERNAME = "6353438333"
PASSWORD = "Pravin@6299"

class Command(BaseCommand):
    help = "Auto-login to Zerodha Kite, get access token, and save to DB"
    print("command called")

    def handle(self, *args, **kwargs):
        driver = None
        try:
            # Launch browser (visible)
            chrome_options = Options()
            chrome_options.add_experimental_option("detach", True)  # Keeps browser open
            driver = webdriver.Chrome(options=chrome_options)

            self.stdout.write("🌐 Opening Zerodha login...")
            driver.get(f"https://kite.zerodha.com/connect/login?v=3&api_key={API_KEY}")
            time.sleep(2)

            # Login
            driver.find_element(By.ID, "userid").send_keys(USERNAME)
            driver.find_element(By.ID, "password").send_keys(PASSWORD)
            driver.find_element(By.XPATH, '//button[@type="submit"]').click()
            time.sleep(2)

            self.stdout.write("⏳ Please manually enter OTP in the browser...")
            for i in range(60):
                current_url = driver.current_url
                if "request_token=" in current_url:
                    break
                time.sleep(1)

            parsed = urllib.parse.urlparse(driver.current_url)
            request_token = urllib.parse.parse_qs(parsed.query).get("request_token", [None])[0]

            if not request_token:
                self.stderr.write("❌ Could not find request_token in redirected URL.")
                return

            # Exchange token
            kite = KiteConnect(api_key=API_KEY)
            session_data = kite.generate_session(request_token, api_secret=API_SECRET)
            access_token = session_data["access_token"]
            kite.set_access_token(access_token)

            KiteToken.objects.create(access_token=access_token, request_token=request_token)

            self.stdout.write(self.style.SUCCESS("✅ Token saved successfully."))
            self.stdout.write(self.style.SUCCESS(f"🔐 Access Token: {access_token}"))

        except Exception as e:
            self.stderr.write(f"❌ Error: {e}")
        finally:
            if driver:
                driver.quit()