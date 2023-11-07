# Restaurant-Monitoring
## Problem statement

The Retaurant monitor rsystem monitors if the store is online or not. All restaurants are supposed to be online during their business hours. Due to some unknown reasons, a store might go inactive for a few hours. Restaurant owners want to get a report of the how often this happened in the past.   

We want to build backend APIs that will help restaurant owners achieve this goal. 

We will provide the following data sources which contain all the data that is required to achieve this purpose. 

## Data sources

We will have 3 sources of data 

1. We poll every store roughly every hour and have data about whether the store was active or not in a CSV.  The CSV has 3 columns (`store_id, timestamp_utc, status`) where status is active or inactive.  All timestamps are in **UTC**
2. We have the business hours of all the stores - schema of this data is `store_id, dayOfWeek(0=Monday, 6=Sunday), start_time_local, end_time_local`
    1. These times are in the **local time zone**
    2. If data is missing for a store, assume it is open 24*7
3. Timezone for the stores - schema is `store_id, timezone_str`
    1. If data is missing for a store, assume it is America/Chicago
    2. This is used so that data sources 1 and 2 can be compared against each other. 


Data cannot be shared publicly

## Data output requirement

We want to output a report to the user that has the following schema

`store_id, uptime_last_hour(in minutes), uptime_last_day(in hours), update_last_week(in hours), downtime_last_hour(in minutes), downtime_last_day(in hours), downtime_last_week(in hours)` 

1. Uptime and downtime should only include observations within business hours. 
2. You need to extrapolate uptime and downtime based on the periodic polls we have ingested, to the entire time interval.
    1. eg, business hours for a store are 9 AM to 12 PM on Monday
        1. we only have 2 observations for this store on a particular date (Monday) in our data at 10:14 AM and 11:15 AM
        2. we need to fill the entire business hours interval with uptime and downtime from these 2 observations based on some sane interpolation logic

Note: The data we have given is a static data set, so you can hard code the current timestamp to be the max timestamp among all the observations in the first CSV.  

## API requirement

1. You need two APIs 
    1. /trigger_report endpoint that will trigger report generation from the data provided (stored in DB)
        1. No input 
        2. Output - report_id (random string) 
        3. report_id will be used for polling the status of report completion
    2. /get_report endpoint that will return the status of the report or the csv
        1. Input - report_id
        2. Output
            - if report generation is not complete, return “Running” as the output
            - if report generation is complete, return “Complete” along with the CSV file with the schema described above.

## Installation & Setup

1. To install the required packages, run the command
```pip install -r requirements.txt```
2. Setup mysql server and update the sql server uri in `config.json` file.
3. Setup redis server and update the server uri in the `config.json` file.
4. Create a folder with name `csv` in root and add the initial data files.

## Usage

1. To Run the server, Run ```python manage.py``` in the root directory.
2. To bring up celery workers, run the following command
```
    celery -A app.celery_config worker --loglevel=INFO
```
3. The flask app runs at `http://localhost:5000`

## API Documentation

1. `/trigger_report` - This endpoint triggers the report generation.
    * Request
        ```
            POST /trigger_report HTTP/1.1
        ```
    * Response
        ```
            HTTP/1.1 200 OK
            Content-Type: application/json

            {
            "report_id": "30fOCJcpdpcGLZbI",
            "status": "success"
            }
        ```

2. `/get_report/report_id` - This endpoint returns the status of the report. If the report is completed it returns a link to download the report.
    * Request
        ```
             GET /get_report/report_id HTTP/1.1
        ```
    * Response
        status - Running
        ```
            {
            "report_id": "30fOCJcpdpcGLZbI",
            "status": "Running"
            }
        ```
        status - Completed
        ```
            {
            "download_url": "http://localhost:5000/download/30fOCJcpdpcGLZbI",
            "report_id": "30fOCJcpdpcGLZbI",
            "status": "Completed"
            }
        ```

3. `/download/report_id` - This endpoint returns the csv file.
    * Request
     ```
        GET /download/report_id HTTP/1.1
     ```


## Architecture

![Architecture.png](https://drive.google.com/file/d/1mgxddDCmoUj8TpYimK7PAH8KY4w4xzXu/view?usp=sharing)

1. Flask APP
2. Data Poling worker
3. Report Generation Worker
4. Redis queue
5. MySQL Database

## Workflow
    1. The Data Poling worker updates the data in mysql db every hour.
    2. The Flask Application interacts with all the components. Where there trigger_report request. The Flask apps inserts the report information in mysql db and communicates with report generation worker using redis queue
    3. The Report generation worker queries data from the mysql db, generates report and updates the status of the report in the mysql db.
    4. The /get_report endpoint checks the status of the report in mysql db. If completed it will generate a url to download the csv file and responds to the rquest.
    5. The download uel consists of /download to serve the csv file

## Note

    Facing some issues with Celery workers picking jobs from the queue. Usinf python's multi threading as a work around untill fixes the issues with celery.
