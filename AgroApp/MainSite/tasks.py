from django_q.tasks import schedule
from django.utils.timezone import now, timedelta
from MainSite.models import Notification, User

def send_weather_notifications():
    message = "Weather Update: Rain expected in the next few hours. Prepare accordingly."
    farmers = User.objects.all()  # Assuming all users are farmers
    for farmer in farmers:
        Notification.objects.create(user=farmer, message=message)

# Schedule it to run every 3 hours
schedule(
    'MainSite.tasks.send_weather_notifications',
     schedule_type='I',  # Interval type
    minutes=2,
    repeats=-1,  # Run indefinitely
    next_run=now() + timedelta(minutes=2)
)
