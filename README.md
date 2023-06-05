# LoopAPI - San Francisco #

LoopAPI is a client side REST API for accessing the triggering and generation of report endpoints.

Tech Stack: Django, Celery, Redis, Pandas, SQLite3, HTML, CSS

Django REST Framework (DRF) was not used as Django FileResponses/HttpResponse doesn't download files
on endpoint receiving a POST request due to rendering issues. Hence I decided to implement the endpoints
using some frontend. Hence don't expect a JSON response :)

Celery beat service was used to perform background downloads of hourly polled store data. Message brokering
queue used was Redis. All reports were processed using Pandas and Swifter for parallel processing. All the data
was stored on SQLite3 database using Django Models.

The logic behind producing the Output Reports are as follows:
Consider a store with time and status.


|       Time       |        Status        |
| ---------------- | -------------------- |
| 09:00            | Active               |
| 10:00            | Inactive             |
| 11:00            | Active               |
| 12:00            | InActive             |
| 13:00            | Active               |
| 14:00            | Active               |
| 15:00            | Active               |
| 16:00            | InActive             |


We first localize all the timestamps in the Store_Poll.csv and Business_Hours.csv using Timezone.csv
We then filter out timestamps that are more than one week old. We also filter timestamps for each store
by ensuring that they are within their business hours. Since we are only given the status of the stores at
different timestamps, we cannot predict uptime or downtime accurately. So what we can do is to count the
no of active status and this will almost give us a better idea. Its count will give us the uptime in hours.
Once we calculate the uptimes based on last_hour, last_day and last_week, We can then directly calculate
downtimes by subtracting the total no of hours in an hour, day and week. Further to improve accuracy, we
find the no of minutes by finding the difference between the latest and earliest timestamps for a particular working day
with respect to the closing and opening hours of the store. We then sum it up with the uptimes. 

The web-app is working perfectly and you can generate an output report as csv file by following the instructions below.
All corner cases and type errors has also been managed.

## Installation ##

Create and activate a virtual environment:

```bash
virtualenv virtualenv-name
```

Download all the required dependencies.

```bash
pip install -r from requirements.txt
```

## Usage ##

Open a terminal to setup Django followed by running the server


```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Open two separate terminals and run the following commands 
This is to start Celery and Redis servers


```bash
celery -A LoopKitchenAPI worker -l info
```

```bash
celery -A LoopKitchenAPI beat -l info
```


If this is the first time running the server, kindly run celery beat service to ensure that the
the required data for triggering reports is installed on the system. This will take 1 hour as the
service is scheduled in that way. Once complete, You can access the following API endpoints !

[`GET /trigger_report`]: Triggers New Report Generations by providing users with unique Report-ID

[`GET /get_report`]: Collects Report Generations using user assigned Report-ID verified at backend

[`POST /get_report`]: Downloads Report Generations using user assigned Report-ID verified at backend


### Authentication ###

Authentication requires a set of JSON credentials. The web app utilizes DriveAPI to perform
background tasks powered by Celery and Redis as message broker queue. You can head over to
google cloud console and generate one for yourself. 

[`https://console.cloud.google.com`]

Credentials present in the repository has been disabled and hence needs to be updated from your side due to security constraints
