import discord
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import asyncio
import requests

TOKEN = ''        #DISCORD BOT TOKEN
CHANNEL_ID = 123  #DISCORD CHANNEL ID
webdelay = 5
delay = 2
nointernet_display = False

license = input("License Number: ")
vnumber = input("Version Number: ")
surname = input("Last Name: ")
dob = input("Date Of Birth: ")
desired_date = input("Date to look from: ")
debug_mode = input("Debug Mode (y/n): \n")
print("Console Log: \n")
print("---------------------------")

async def is_connected():
    try:
        requests.get('https://online.nzta.govt.nz/licence-test/identification', timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Web scraping function
async def scrape_dates():
    datearr_xpath = []
    datearr_num = []
    desired_datearr_xpath = []
    desired_datearr_num = []
    dates_available = []

    driver = webdriver.Chrome(service=Service(''))  #DIRECTORY TO WEBDRIVER FROM 'https://googlechromelabs.github.io/chrome-for-testing/'
    driver.set_window_size(800, 600)
    driver.get("https://online.nzta.govt.nz/licence-test/identification")

    p_license = '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[1]/div/div/input'
    p_vnumber = '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[2]/div/div/input'
    p_surname = '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[3]/div/div/input'
    p_dob = '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[4]/div/div/input'
    p_login = '//*[@id="btnContinue"]'
    p_reschedule = '//*[@id="btnContinue"]'
    p_region = '//*[@id="nzta-main-content"]/app-test-site/div[2]/div/ul/li[5]/a'
    p_county = '//*[@id="nzta-main-content"]/app-test-site/div[2]/div[2]/ul/li[4]/a'
    p_place = '//*[@id="nzta-main-content"]/app-test-site/div[2]/div[3]/ul/li[2]/a'
    
    try:
        await asyncio.sleep(webdelay)
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

        element = driver.find_element(By.XPATH, p_reschedule)
        element.click()

        await asyncio.sleep(webdelay)

        element = driver.find_element(By.XPATH, p_region)
        element.click()
        element = driver.find_element(By.XPATH, p_county)
        element.click()
        element = driver.find_element(By.XPATH, p_place)
        element.click()

        await asyncio.sleep(webdelay)

        for i in range(5):
            for t in range(7):
                p_date = '//*[@id="datePicker"]/table/tbody/tr['+str(i+1)+']/td['+str(t+1)+']'
                element = driver.find_element(By.XPATH, p_date)
                if element.text != "":
                    datearr_xpath.append(p_date)
                    datearr_num.append(element.text)
        
        for item in datearr_num:
            if int(item) >= int(desired_date):
                itemindex = datearr_num.index(item)
                desired_datearr_xpath.append(datearr_xpath[itemindex])
                desired_datearr_num.append(item)
        
        for item in desired_datearr_xpath:
            element = driver.find_element(By.XPATH, item)
            itemindex = desired_datearr_xpath.index(item)
            element_class = element.get_attribute('class')
            if element_class != "ui-state-disabled":
                if element_class != "ui-state-disabled ui-datepicker-today":
                    dates_available.append(desired_datearr_num[itemindex])
    
    except Exception as e:
        if debug_mode == "y":
            print(f"Couldn't find xpath: {e}")

    driver.quit()
    return dates_available



intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')
    
async def check_and_send_dates():
    while True:
        if await is_connected():
            if client.is_ready():
                try:
                    dates_available = await scrape_dates()
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
            if nointernet_display:
                print("No internet connection")
                nointernet_display = False
        await asyncio.sleep(delay)


async def main():
    while True:
        try:
            await client.start(TOKEN)
        except Exception as e:
            if debug_mode == "y":
                print(f"An error occurred: {e}")

loop = asyncio.get_event_loop()
loop.create_task(check_and_send_dates())
loop.run_until_complete(main())

