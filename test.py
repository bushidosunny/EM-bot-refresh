

from datetime import datetime
import pytz

timezone = pytz.timezone("America/Los_Angeles")
current_time = datetime.now(timezone)
formatted_time = current_time.strftime("%H:%M:%S")
print(formatted_time)
