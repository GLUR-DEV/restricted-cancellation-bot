# restricted-cancellation-bot

A small bot that watches the NZ restricted licence driving test booking site and pings you on Discord when a slot opens up (e.g. someone cancels).

It uses Selenium to log in to the NZTA booking site with your licence details, opens the calendar for a test site, and checks for days that aren't greyed out. Any available day on or after the date you choose is posted to a Discord channel with an `@everyone` ping.

## Requirements

- Python 3.8+
- Google Chrome and a matching [chromedriver](https://googlechromelabs.github.io/chrome-for-testing/)
- A Discord bot token, with the bot added to your server and able to post in the target channel
- Python packages: `discord.py`, `selenium`, `requests`

```bash
pip install discord.py selenium requests
```

## Setup

Open `main.py` and fill in the commented fields:

| Setting | Where | What it is |
| --- | --- | --- |
| `TOKEN` | top of file | Your Discord bot token |
| `CHANNEL_ID` | top of file | ID of the channel to post alerts in |
| `Service('')` | in `scrape_dates()` | Path to your chromedriver executable |
| `p_region`, `p_county`, `p_place` | in `scrape_dates()` | XPaths for the region → county → test site to check. Change the `li[N]` index to pick your location |

## Usage

```bash
python main.py
```

You'll be prompted for:

- **License Number**, **Version Number**, **Last Name**, **Date Of Birth**: your licence details, entered the way the NZTA site expects them
- **Date to look from**: a day of the month (e.g. `15`). Earlier days are ignored
- **Debug Mode (y/n)**: `y` prints errors that are otherwise hidden

Leave it running. It checks continuously and posts to Discord whenever it finds an open day.

## Known issues

- **Brittle selectors.** The scraper uses hard-coded XPaths, so it will stop working if NZTA changes their site. Updating the XPaths in `scrape_dates()` is the fix.
- **Day-of-month only.** "Date to look from" compares day numbers, not full dates, so it doesn't account for the month.
- **Possible crash on connection loss.** `nointernet_display` is assigned inside `check_and_send_dates()` without a `global` declaration, which can raise an `UnboundLocalError` when the internet drops.
- **No rate limiting beyond short sleeps.** It reloads the booking site every few seconds; consider increasing `delay` and `webdelay` to be kind to the site.
- Your licence details are entered at runtime and never stored, but the bot token lives in `main.py`, so don't commit it.

## Disclaimer

This project is unofficial and not affiliated with NZTA. Use it at your own risk and check the site's terms of use.
