import uuid
from datetime import datetime, timedelta

import telnyx
from celery import Celery
from flask import Flask, request, render_template, flash

app = Flask(__name__)
app.secret_key = uuid.uuid4()
app.config.from_pyfile('config_file.cfg')
celery = Celery('schedule_meeting_server', broker='redis://localhost:6379')

telnyx.api_key = app.config['API_KEY']


@celery.task
def send_reminder(to, message):
    telnyx.Message.create(
        to=to,
        from_=app.config['FROM_NUMBER'],
        text=message
    )


@app.route('/', methods=['GET', 'POST'])
def schedule_meeting():
    if request.method == "POST":
        meeting_date = datetime.strptime(request.form['meeting_date'], '%Y-%m-%d')
        meeting_time = datetime.strptime(request.form['meeting_time'], '%H:%M').time()
        meetingDT = datetime.combine(meeting_date, meeting_time)

        now = datetime.now()

        if meetingDT - timedelta(hours=3, minutes=5) < now:
            flash('Appointmenttest time must be at least 3:05 hours from now')
            return render_template('index.html')

        meetingDT = meetingDT - timedelta(hours=3)

        message = "{customer_name}, you have a meeting scheduled for {meeting_time}".format(customer_name=request.form['customer_name'], meeting_time=str(meetingDT))
        to = "{country_code}{phone}".format(country_code=app.config['COUNTRY_CODE'], phone=request.form['phone'])

        send_reminder.apply_async([to, message], eta=meetingDT)

        return render_template('success.html', name=request.form['customer_name'], meeting_name=request.form['meeting_name'],
                               phone=request.form['phone'], meetingDT=str(meetingDT))

    return render_template('index.html')


if __name__ == '__main__':
    app.run(port=5010)
