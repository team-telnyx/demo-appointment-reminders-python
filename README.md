# Appointment Reminder

### Environment setup

To setup our environment, we’re going to install the appropriate packages into a new virtualenv. Virtualenvs allow us to keep Python dependencies independent from project to project.

```bash
virtualenv --no-site-packages .scheduler_env
. .scheduler_env/bin/activate
pip install telnyx, Flask, celery, redis
```

There are a few tools we are going to employ apart from the Telnyx Python Library: Flask allows us to setup a simple HTTP server, Celery will let us schedule meeting reminders for the future, and Redis serves as the backend for Celery.

### Configuration

Create a `config.cfg` file in your project directory. Flask will load this at startup. First, head into the [Telnyx Portal](https://portal.telnyx.com/#/app/numbers/search-numbers), provision an SMS enabled number and [Messaging Profile](https://portal.telnyx.com/#/app/messaging), and create an [API Key](https://portal.telnyx.com/#/app/auth/v2). Then add those to the config file.

```
API_KEY='YOUR_API_KEY'
FROM_NUMBER='YOUR_TELNYX_NUMBER'
```
> **Note:** This file contains a secret key, it should not be committed to source control.

We’ll also place Flask in debug mode and assume all numbers are in the U.S.

```
DEBUG=True
COUNTRY_CODE='+1'
```

### Server Initialization

The first piece of our application sets up the Telnyx library, Flask, and Celery.

```python
app = Flask(__name__)
app.secret_key = uuid.uuid4()
app.config.from_pyfile('config_file.cfg')
celery = Celery('schedule_meeting_server', broker='redis://localhost:6379')

telnyx.api_key = app.config['API_KEY']
```

### Collect User Input

Create a simple HTML form which collects the meeting date, time, customer name, and phone number. The full HTML source can be found in our GitHub repo, and we’ll serve it with the following Flask route: `@app.route('/', methods=['GET', 'POST'])`.

### Implement the SMS Notification

Create a simple function that sends an SMS message parameterized on the destination number and message. The decorator `@celery.task` allows us to schedule this function to run in the future.

```python
@celery.task
def send_reminder(to, message):
    telnyx.Message.create(
        to=to,
        from_=app.config['FROM_NUMBER'],
        text=message
    )
```

> **Note:** `from` is a reserved word in Python. The Telnyx Python Library adds an underscore character to any parameter that would conflict with a reserved keyword.

### Parse User Input and Schedule the Message

Setup our route which will handle both `GET` and `POST` requests.

```python
@app.route('/', methods=['GET', 'POST'])
def schedule_meeting():
    if request.method == "POST":
        # ...
    return render_template('index.html')
```

Now, within the conditional, first parse the user date/time input.

```python
meeting_date = datetime.strptime(request.form['meeting_date'], '%Y-%m-%d')
meeting_time = datetime.strptime(request.form['meeting_time'], '%H:%M').time()
meeting_datetime = datetime.combine(meeting_date, meeting_time)
```

Next, only allow meetings to be scheduled that are three hours and five minutes in the future or later.

```python
now = datetime.now()
if meeting_datetime - timedelta(hours=3, minutes=5) < now:
    flash('Appointment time must be at least 3:05 hours from now')
    return render_template('index.html')
```

Then, compute the reminder time and message, and schedule the reminder.

### Remind the User

Remond the user 3 hours before the meeting.

```python
reminder_datetime = meeting_datetime - timedelta(hours=3)

message = "{customer_name}, you have a meeting scheduled for {meeting_time}".format(customer_name=request.form['customer_name'], meeting_time=str(meeting_datetime))
to = "{country_code}{phone}".format(country_code=app.config['COUNTRY_CODE'], phone=request.form['phone'])

send_reminder.apply_async([to, message], eta=reminder_datetime)
```

Finally, render the success template.

```python
return render_template('success.html',
                       name=request.form['customer_name'],
                       meeting_name=request.form['meeting_name'],
                       phone=request.form['phone'],
                       meeting_datetime=str(meeting_datetime))
```

And at the end of the file, start the server.

```python
if __name__ == '__main__':
    app.run(port=5010)
```

### Running the Project

Make sure [redis](https://redis.io/topics/quickstart) is running in the background, and then start the Celery task and Python server. Assuming your code is in `schedule_meeting_server.py`.

```bash
celery -A schedule_meeting_server.celery worker
python schedule_meeting_server.py
```
