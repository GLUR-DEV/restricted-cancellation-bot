"""
restricted-cancellation-bot

Watches the NZTA online booking site for NZ restricted licence driving tests
and posts to a Discord channel when a day opens up (e.g. someone cancels).

How it works:
  1. A Selenium-driven Chrome window logs into the NZTA "reschedule" flow
     using your licence details.
  2. It navigates to a specific test site and reads the calendar.
  3. Any day on/after your chosen day-of-month that isn't greyed out is
     reported to Discord via a bot, pinging @everyone.
  4. Repeat forever.

NOTE: the scraper relies on hard-coded XPaths and the exact layout of the
NZTA site, so it will break whenever they change the page.
"""

import discord
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import asyncio
import requests

# ---------------------------------------------------------------------------
# Configuration -- fill these in before running
# ---------------------------------------------------------------------------
TOKEN = ''        # DISCORD BOT TOKEN
CHANNEL_ID = 123  # DISCORD CHANNEL ID (the channel alerts get posted to)

webdelay = 5      # seconds to wait for the NZTA pages to load between steps
delay = 2         # seconds between short actions / between scrape cycles
nointernet_display = False  # used to avoid spamming "No internet" messages

# ---------------------------------------------------------------------------
# User input (asked once at startup)
# ---------------------------------------------------------------------------
license = input("License Number: ")
vnumber = input("Version Number: ")        # the licence "version" number
surname = input("Last Name: ")
dob = input("Date Of Birth: ")             # typed exactly as the site expects it
desired_date = input("Date to look from: ")  # day of the month (e.g. 15); earlier days are ignored
debug_mode = input("Debug Mode (y/n): \n")  # "y" prints errors that are otherwise swallowed
print("Console Log: \n")
print("---------------------------")


async def is_connected():
    """Return True if the NZTA site is reachable, False if there's no connection."""
    try:
        requests.get('https://online.nzta.govt.nz/licence-test/identification', timeout=5)
        return True
    except requests.ConnectionError:
        return False


# Web scraping function
async def scrape_dates():
    """
    Open the NZTA booking site, walk through the login/reschedule flow, and
    return a list of available day-of-month strings (e.g. ['17', '23']) that
    are on or after `desired_date`. Returns an empty list if nothing is open
    or if any step of the scrape fails.
    """
    datearr_xpath = []          # XPath of every non-empty calendar cell
    datearr_num = []            # the day number shown in each of those cells
    desired_datearr_xpath = []  # XPaths of cells on/after the desired date
    desired_datearr_num = []    # day numbers of those cells
    dates_available = []        # final result: days that are actually bookable

    # Launch Chrome. The Service() path must point at your chromedriver binary.
    driver = webdriver.Chrome(service=Service(''))  # DIRECTORY TO WEBDRIVER FROM 'https://googlechromelabs.github.io/chrome-for-testing/'
    driver.set_window_size(800, 600)
    driver.get("https://online.nzta.govt.nz/licence-test/identification")

    # XPaths for the elements we interact with. These are brittle: if NZTA
    # changes their page layout, these are what need updating.
    p_license = '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[1]/div/div/input'
    p_vnumber = '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[2]/div/div/input'
    p_surname = '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[3]/div/div/input'
    p_dob = '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[4]/div/div/input'
    p_login = '//*[@id="btnContinue"]'       # "Continue" button on the login form
    p_reschedule = '//*[@id="btnContinue"]'  # "Continue" button on the next screen (reschedule)
    # The three below are list items in the site picker (region -> county -> test site).
    # The li[N] index decides WHICH location gets checked; change it to pick yours.
    p_region = '//*[@id="nzta-main-content"]/app-test-site/div[2]/div/ul/li[5]/a'
    p_county = '//*[@id="nzta-main-content"]/app-test-site/div[2]/div[2]/ul/li[4]/a'
    p_place = '//*[@id="nzta-main-content"]/app-test-site/div[2]/div[3]/ul/li[2]/a'

    try:
        # --- Step 1: log in with licence details ---
        await asyncio.sleep(webdelay)  # let the page finish loading
        element = driver.find_element(By.XPATH, p_license)
        element.send_keys(license)
        element = driver.find_element(By.XPATH, p_vnumber)
        element.send_keys(vnumber)
        element = driver.find_element(By.XPATH, p_surname)
        element.send_keys(surname)
        element = driver.find_element(By.XPATH, p_dob)
        element.send_keys(dob)
        element = driver.find_element(By.XPATH, p_login)
        await asyncio.sleep(delay)
        element.click()

        await asyncio.sleep(webdelay)

        # --- Step 2: continue into the reschedule flow ---
        element = driver.find_element(By.XPATH, p_reschedule)
        element.click()

        await asyncio.sleep(webdelay)

        # --- Step 3: pick the region, county and test site to check ---
        element = driver.find_element(By.XPATH, p_region)
        element.click()
        element = driver.find_element(By.XPATH, p_county)
        element.click()
        element = driver.find_element(By.XPATH, p_place)
        element.click()

        await asyncio.sleep(webdelay)

        # --- Step 4: read the calendar ---
        # The date picker is a table of up to 5 week rows x 7 day columns.
        # Collect every cell that actually contains a day number (blank cells
        # are padding from the previous/next month).
        for i in range(5):
            for t in range(7):
                p_date = '//*[@id="datePicker"]/table/tbody/tr['+str(i+1)+']/td['+str(t+1)+']'
                element = driver.find_element(By.XPATH, p_date)
                if element.text != "":
                    datearr_xpath.append(p_date)
                    datearr_num.append(element.text)

        # Keep only the days on or after the user's "look from" day.
        # (Only compares day-of-month numbers, so it doesn't know about months.)
        for item in datearr_num:
            if int(item) >= int(desired_date):
                itemindex = datearr_num.index(item)
                desired_datearr_xpath.append(datearr_xpath[itemindex])
                desired_datearr_num.append(item)

        # A day is bookable if its cell isn't styled as disabled. Today's
        # date is also styled "disabled", so it's excluded as well.
        for item in desired_datearr_xpath:
            element = driver.find_element(By.XPATH, item)
            itemindex = desired_datearr_xpath.index(item)
            element_class = element.get_attribute('class')
            if element_class != "ui-state-disabled":
                if element_class != "ui-state-disabled ui-datepicker-today":
                    dates_available.append(desired_datearr_num[itemindex])

    except Exception as e:
        # Most commonly an XPath that no longer matches (site changed, page
        # was slow, or login failed). Silent unless debug mode is on.
        if debug_mode == "y":
            print(f"Couldn't find xpath: {e}")

    driver.quit()  # always close the browser so windows don't pile up
    return dates_available



# ---------------------------------------------------------------------------
# Discord bot setup
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    """Called by discord.py once the bot has connected successfully."""
    print(f'Logged in as {client.user.name}')


async def check_and_send_dates():
    """
    Main polling loop: scrape the NZTA site over and over and post any
    available dates to the Discord channel. Runs forever alongside the bot.
    """
    while True:
        if await is_connected():
            # Wait until the Discord client is logged in before scraping
            if client.is_ready():
                try:
                    dates_available = await scrape_dates()
                    # NOTE: this assignment makes `nointernet_display` a local
                    # variable in this function (no `global` declaration), so
                    # the check in the `else` branch below can raise
                    # UnboundLocalError when the connection drops.
                    nointernet_display = True
                    if dates_available:
                        channel = client.get_channel(CHANNEL_ID)
                        if channel:
                            await channel.send('@everyone ' + str(dates_available))
                            await asyncio.sleep(delay)
                except Exception as e:
                    if debug_mode == "y":
                        print(f"An error occurred: {e}")
        else:
            # Intended to print "No internet connection" once per outage
            if nointernet_display:
                print("No internet connection")
                nointernet_display = False
        await asyncio.sleep(delay)


async def main():
    """Start the Discord bot, restarting it if it ever crashes or disconnects."""
    while True:
        try:
            await client.start(TOKEN)
        except Exception as e:
            if debug_mode == "y":
                print(f"An error occurred: {e}")


# Run the polling loop as a background task, with the Discord bot in the foreground.
loop = asyncio.get_event_loop()
loop.create_task(check_and_send_dates())
loop.run_until_complete(main())
