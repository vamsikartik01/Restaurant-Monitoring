from app.celery_config import celery
from app import app, db
from app.models.reports import Reports
from app.models.store_status import StoreStatus
from app.models.menu_hours import MenuHours
from app.models.timezones import Timezones
import time
import threading
import pandas as pd
from datetime import datetime, timedelta
import pytz
from config import config

# start report generation instace concurrently
def start_report(report_id):
    thread = threading.Thread(target=generate_report,args=(report_id,))
    thread.start()

# function to query db
def fetch_data_to_pd():
    try:
        print("started fetching data from db")
        with app.app_context():
            store_data_raw = StoreStatus.query.all()
            store_data_list = [record.__dict__ for record in store_data_raw]
            df_store_data = pd.DataFrame(store_data_list)

            menu_hours_raw = MenuHours.query.all()
            menu_hours_list = [record.__dict__ for record in menu_hours_raw]
            df_menu_hours = pd.DataFrame(menu_hours_list)

            timezones_raw = Timezones.query.all()
            timezone_list = [record.__dict__ for record in timezones_raw]
            df_timezones = pd.DataFrame(timezone_list)
            return df_store_data, df_menu_hours, df_timezones

    except Exception as e:
        print(e)

# this function converts menu_hours start_time_local, end_time_local into ust
def convert_into_utc(row):
    tz = pytz.timezone(row['timezone_str'])

    start_hour, start_minute, start_second = map(int, str(row.start_time_local).split(':'))
    end_hour, end_minute, end_second = map(int, str(row.end_time_local).split(':'))

    # local start and end time with random date 
    start_time_local = tz.localize(datetime(2023, 1, 2, start_hour, start_minute, start_second))
    end_time_local = tz.localize(datetime(2023, 1, 2, end_hour, end_minute, end_second))
    # converting local time into ust
    start_time_utc = start_time_local.astimezone(pytz.UTC)
    end_time_utc = end_time_local.astimezone(pytz.UTC)
    
    # checking the weekday. it might slip to next weekday or previous one
    if start_time_utc.day < 2:
        if row.day == 0:
            new_day_start = 6
        else:
            new_day_start = row.day - 1
    elif start_time_utc.day > 2:
        if row.day == 6:
            new_day_start = 0
        else:
            new_day_start = row.day + 1
    else:
        new_day_start = row.day

    if end_time_utc.day < 2:
        if row.day == 0:
            new_day_end = 6
        else:
            new_day_end = row.day - 1
    elif end_time_utc.day > 2:
        if row.day == 6:
            new_day_end = 0
        else:
            new_day_end = row.day + 1
    else:
        new_day_end = row.day

    # if end time slips to next day or start time slips to previous day
    if start_time_utc.time() > end_time_utc.time():
        start_time_split = datetime(2023, 1, 2, 0, 0, 0)
        end_time_split = datetime(2023, 1, 2, 23, 59, 59)

        row_split1 = row.copy() 
        row_split2 = row.copy()

        # split the menu_hours rows as follows
        # first start_time_ust to 23:59:59 ust
        # second 00:00:00 ust to end_time_ust 
        row_split1['start_time_utc'] = start_time_utc.astimezone(pytz.UTC).time()
        row_split1['end_time_utc'] = end_time_split.time()
        row_split1['day_utc'] = new_day_start

        row_split2['start_time_utc'] = start_time_split.time()
        row_split2['end_time_utc'] = end_time_utc.astimezone(pytz.UTC).time()
        row_split2['day_utc'] = new_day_end

        return [row_split1, row_split2]


    row['start_time_utc'] = start_time_utc.astimezone(pytz.UTC).time()
    row['end_time_utc'] = end_time_utc.astimezone(pytz.UTC).time()
    row['day_utc'] = new_day_start 
    return [row]

# update the database with report status completed.
def mark_complete(report_id):
    try:
        with app.app_context():
            report = Reports.query.filter_by(report_id=report_id).first()
            report.complete()
            db.session.commit()
            print("marked complete")
    except Exception as e:
        print(e)

# update the database with report status failed
def mark_failed(report_id):
    try:
        with app.app_context():
            report = Reports.query.filter_by(report_id=report_id).first()
            report.failed()
            db.session.commit()
            print("marked failed")
    except Exception as e:
        print(e)

# Report generation function which runs concurrently to generate reports
#@celery.task
def generate_report(report_id):
    try:
        print("generating")
        with app.app_context():
            # fetch queried data from db
            df_poling, df_menu_hours, df_timezones = fetch_data_to_pd()

            # find unique store ids in poling(store status)csv these are the total store ids in the final report
            df_stores = df_poling['store_id'].unique() ## array

            # merge menu_hours dataframe with timezones dataframe on left
            df_time = pd.merge(df_menu_hours, df_timezones, on='store_id', how='left')
            # request time is report triggered timestamp in this case it is max from the poling from the csv
            request_timestamp = df_poling['timestamp_utc'].max()
            request_timestamp = pd.to_datetime(request_timestamp, format="mixed", dayfirst=False, utc=True)

            # calculate time stamps needed for all stages of report generation
            time_format = '%Y-%m-%d %H:%M:%S.%f UTC'
            one_hour_ago = (request_timestamp - timedelta(hours=1)).strftime(time_format)
            one_day_ago = (request_timestamp - timedelta(days=1)).strftime(time_format)
            one_week_ago = (request_timestamp - timedelta(weeks=1)).strftime(time_format)
            
            result = []
            
            # iterate through each store id from the unique store ids in poling csv to calculate required uptimes and downtimes
            for store in df_stores[:config['app_batch_size']]:
                open_all = False
                df_store_status = df_poling[df_poling['store_id'] == store]
                # if there is no entry with store id present the store is open all the time.
                if store in df_time['store_id'].values:
                    df_store_times = df_time[df_time.store_id == store]
                    converted_dfs = []
                    for _, row in df_store_times.iterrows():
                        converted_dfs.extend(convert_into_utc(row))

                    df_store_times_utc = pd.DataFrame(converted_dfs)
                else:
                    open_all = True
                
                # timestamps data generated for last hour in minutes
                timestamps_last_hour = pd.date_range(start=one_hour_ago, end=request_timestamp, freq='T')
                df_last_hour = pd.DataFrame({'timestamp':timestamps_last_hour})

                df_store_status['timestamp_utc'] = pd.to_datetime(df_store_status['timestamp_utc'], utc=True)
                uptimehr = 0
                downtimehr = 0

                # iterating through each timestamp to calculate the uptime and downtime
                for timestamp in timestamps_last_hour[1:]:
                    # check for closed hours we count 0 for timestamps lies in non active hours of the store.
                    if not open_all:
                        # get the store open times from the df converted below and check
                        store_times = df_store_times_utc[df_store_times_utc['day'] == timestamp.weekday()]
                        if not store_times.empty:
                            times = []
                            for time in store_times.iterrows():
                                times.append([time[1][5], time[1][6]])

                            lies = False
                            for time in times:
                                if str(timestamp.time()) >= str(time[0]) and str(timestamp.time()) <= str(time[1]):
                                    lies = True

                            if not lies:
                                break
                        
                    # to perform interpolation to find the status of the store, we need status of two nearest timestamps
                    idx,idx2 = (df_store_status['timestamp_utc']-timestamp).abs().nsmallest(2).index
                
                    neibhour1 = df_store_status[df_store_status.index==idx]
                    neibhour2 = df_store_status[df_store_status.index==idx2]

                    # perform interpolation
                    num = pd.to_datetime(timestamp).timestamp() - pd.to_datetime(neibhour1['timestamp_utc'].values[0]).timestamp()
                    den = pd.to_datetime(neibhour2['timestamp_utc'].values[0]).timestamp() - pd.to_datetime(neibhour1['timestamp_utc'].values[0]).timestamp()
                    
                    if den == 0:
                        weight = 0
                    else:
                        weight = num/den
                    interpolated_status = neibhour1['status'].values[0] if weight < 0.5 else neibhour2['status'].values[0]
            
                    if interpolated_status == "active":
                        uptimehr += 1
                    else:
                        downtimehr += 1

                # Repeat the same process for last day with timestamps in hours
                timestamps_last_day = pd.date_range(start=one_day_ago, end=request_timestamp, freq='H')
                uptimeday, downtimeday = 0,0
                for timestamp in timestamps_last_day[1:]:
                    if not open_all:
                        store_times = df_store_times_utc[df_store_times_utc['day'] == timestamp.weekday()]
                        if not store_times.empty:
                            times = []
                            for time in store_times.iterrows():
                                times.append([time[1][5], time[1][6]])

                            lies = False
                            for time in times:
                                if str(timestamp.time()) >= str(time[0]) and str(timestamp.time()) <= str(time[1]):
                                    lies = True

                            if not lies:
                                break
                        

                    idx,idx2 = (df_store_status['timestamp_utc']-timestamp).abs().nsmallest(2).index
                
                    neibhour1 = df_store_status[df_store_status.index==idx]
                    neibhour2 = df_store_status[df_store_status.index==idx2]

                    num = pd.to_datetime(timestamp).timestamp() - pd.to_datetime(neibhour1['timestamp_utc'].values[0]).timestamp()
                    den = pd.to_datetime(neibhour2['timestamp_utc'].values[0]).timestamp() - pd.to_datetime(neibhour1['timestamp_utc'].values[0]).timestamp()
                    
                    if den == 0:
                        weight = 0
                    else:
                        weight = num/den
                    interpolated_status = neibhour1['status'].values[0] if weight < 0.5 else neibhour2['status'].values[0]
            
                    if interpolated_status == "active":
                        uptimeday += 1
                    else:
                        downtimeday += 1

                # Repeat the same process for last week with timestamps in hours
                timestamps_last_week = pd.date_range(start=one_week_ago, end=request_timestamp, freq='H')
                uptimeweek, downtimeweek = 0,0
                for timestamp in timestamps_last_week[1:]:
                    if not open_all:
                        store_times = df_store_times_utc[df_store_times_utc['day'] == timestamp.weekday()]
                        if not store_times.empty:
                            times = []
                            for time in store_times.iterrows():
                                times.append([time[1][5], time[1][6]])

                            lies = False
                            for time in times:
                                if str(timestamp.time()) >= str(time[0]) and str(timestamp.time()) <= str(time[1]):
                                    lies = True

                            if not lies:
                                break
                        

                    idx,idx2 = (df_store_status['timestamp_utc']-timestamp).abs().nsmallest(2).index
                
                    neibhour1 = df_store_status[df_store_status.index==idx]
                    neibhour2 = df_store_status[df_store_status.index==idx2]

                    num = pd.to_datetime(timestamp).timestamp() - pd.to_datetime(neibhour1['timestamp_utc'].values[0]).timestamp()
                    den = pd.to_datetime(neibhour2['timestamp_utc'].values[0]).timestamp() - pd.to_datetime(neibhour1['timestamp_utc'].values[0]).timestamp()
                    
                    if den == 0:
                        weight = 0
                    else:
                        weight = num/den
                    interpolated_status = neibhour1['status'].values[0] if weight < 0.5 else neibhour2['status'].values[0]
            
                    if interpolated_status == "active":
                        uptimeweek += 1
                    else:
                        downtimeweek += 1


                row = {'store_id':store,'uptime_last_hour(in minutes)': uptimehr,'uptime_last_day(in hours)': uptimeday,'uptime_last_week(in hours)':uptimeweek,
                                        'downtime_last_hour(in minutes)':downtimeweek,'downtime_last_day(in hours)':downtimeday,'downtime_last_week(in hours)':downtimeweek}

                result.append(row)

            # convert the results into a pandas dataframe
            result = pd.DataFrame(result)
            #store the pandas dataframe as csv.
            result.to_csv("reports/"+report_id+".csv", index=False)
            # mark the status as complete for the report
            mark_complete(report_id)

            print("completed generation")
    except Exception as e:
        print("error",e)
        # mark the status as failed for the report
        mark_failed(report_id)