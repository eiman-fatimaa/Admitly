from sympy import python
python
import os
from dotenv import load_dotenv

load_dotenv()

NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#grad-apps")