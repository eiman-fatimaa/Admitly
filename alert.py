python
from fastn import FastnClient
from config import SLACK_CHANNEL

fastn = FastnClient()

def send_alert(school: str, missing_items: list[str], days_until_deadline: int):
    text = (
        f"⚠️ *{school}* — {len(missing_items)} item(s) still missing, "
        f"deadline in {days_until_deadline} day(s): " + ", ".join(missing_items)
    )
    fastn.slack.send_message(channel=SLACK_CHANNEL, text=text)