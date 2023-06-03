import os
import pandas as pd
import swifter
from celery import shared_task
from LoopKitchenAPI.celery import app


from .models import StoreStatus, StoreTimezone, BusinessHours
import os
from pandas import read_csv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO

import time
import pytz
from pytz import timezone
from datetime import datetime, timedelta

import logging
from celery.utils.log import get_task_logger



logger = get_task_logger(__name__)
file_handler = logging.FileHandler(os.path.dirname(__file__) + '/log/errors.log')
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)


@shared_task(bind=True)
def report_generation(self):
    try:
        df1 = pd.read_csv(os.path.dirname( __file__ ) +'/GeneratedReports/PolledS.csv')
        df2 = pd.read_csv(os.path.dirname( __file__ ) +'/GeneratedReports/BusinessH.csv')
        df3 = pd.read_csv(os.path.dirname( __file__ ) +'/GeneratedReports/TimeZoneS.csv')
        #Cleaning and filling the missing data
        df1 = df1.drop('Unnamed: 0', axis = 1)
        df2 = df2.drop('Unnamed: 0', axis = 1)
        df3 = df3.drop('Unnamed: 0', axis = 1)
        set_df3 = set(df3['store_id'])
        set_df1 = set(df1['store_id'])
        missing_store_ids = list(set_df1 - set_df3)
        for store_id in missing_store_ids:
            df3.loc[len(df3.index)] = [store_id,'America/Chicago']
        #Date Time Stamps of df1 are not all of same format as some have milliseconds while others don't. So we filter them out.
        df1['timestamp_utc'] = pd.to_datetime(df1['timestamp_utc'], errors='coerce')
        df1 = df1.dropna(subset=['timestamp_utc'])
        #Converting the timestamps of df1 to datetime objects
        df = pd.DataFrame(df1['timestamp_utc'].copy())
        df1.loc[:,'timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], format='%Y-%m-%d %H:%M:%S.%f %Z')
        #Converting Business Hours to the right datetime format
        set_df3 = set(df3['store_id'])
        set_df2 = set(df2['store_id'])
        # Find store_ids in df3 that are not in df2
        missing_store_ids = list(set_df3 - set_df2)
        # Using Dictionary for faster processing
        dict_list = df2.to_dict('records')
        for store_id in missing_store_ids:
            for i in range(7):
                new_rows = {'store_id':store_id, 'day':i, 'start_time_local':'00:00:00', 'end_time_local':'23:59:59'}
                dict_list.append(new_rows)        
        df2 = pd.DataFrame.from_dict(dict_list)
        # Filtering out polled store data of only the dates for last 1 week
        end_date = df1['timestamp_utc'].max()
        start_date = end_date - timedelta(days=7)
        df1 = df1[(df1['timestamp_utc'] >= start_date) & (df1['timestamp_utc'] <= end_date)]
        #Localization Of The TimeStamps
        timezone_dict = dict(zip(df3['store_id'], df3['timezone_str']))
        #Parallel Processing Using Swifter
        df1['timestamp_utc'] = df1.swifter.apply((lambda row: pd.Timestamp(row['timestamp_utc']).tz_convert(timezone_dict[row['store_id']])), axis=1)
        df1['day'] = df1['timestamp_utc'].swifter.apply(lambda x: x.weekday())
        df1['time'] = df1['timestamp_utc'].swifter.apply(lambda x: x.time())
        df1['date'] = df1['timestamp_utc'].swifter.apply(lambda x: x.date())
        business_hour_dict = {(row['store_id'], row['day']): [row['start_time_local'], row['end_time_local']] for _, row in df2.iterrows()}
        df1['business_start_hour'], df1['business_end_hour'] = zip(*df1.swifter.apply(lambda x: business_hour_dict.get((x['store_id'], x['day']), (None, None)), axis=1))
        df1 = df1[df1['business_start_hour'].notna()]
        df = df1.sort_values(['store_id', 'date'])
        count_df = df[df['status'] == 'active'].groupby(['store_id', 'date'])['status'].value_counts().reset_index()
        daily = pd.DataFrame(count_df)
        df4 = pd.DataFrame({
        'store_id': [],
        'uptime_last_hour':[],
        'uptime_last_day':[],
        'uptime_last_week':[],
        'downtime_last_hour':[],
        'downtime_last_day':[],
        'downtime_last_week':[]
        })
        last_week = daily.groupby(['store_id'])['count'].sum().reset_index()
        last_week = pd.DataFrame(last_week)    
        last_day = daily.groupby(['store_id'])['date'].max().reset_index()
        last_day = last_day.merge(daily, on=['store_id', 'date'])
        last_hour = df[df['status'] == 'active'].groupby(['store_id', 'time'])['status'].value_counts().reset_index()
        last_hour = last_hour.sort_values(by=['store_id', 'time'], ascending=[True, False]).groupby('store_id').head(2)
        last_hour['rank'] = last_hour.groupby('store_id').cumcount() + 1
        last_hour = last_hour.pivot(index='store_id', columns='rank', values='time').reset_index()
        last_hour.columns = ['store_id', 'latest_time1', 'latest_time2']
        lh = last_hour.dropna(how='any')
        t = set()
        for i in lh['latest_time1']:
            t.add(type(i))
            if isinstance(i,float):
                print(i)

        last_hour['h1'] = lh['latest_time1'].swifter.apply(lambda x: int(x.hour))
        last_hour['h2'] = lh['latest_time2'].swifter.apply(lambda x: int(x.hour))
        last_hour['m1'] = lh['latest_time1'].swifter.apply(lambda x: int(x.minute))
        last_hour['m2'] = lh['latest_time2'].swifter.apply(lambda x: int(x.minute))
        last_hour['uptime_last_hour'] = ((last_hour['h1'] - last_hour['h2'])/60) + (last_hour['m1'] - last_hour['m2'])
        df4[['store_id', 'uptime_last_week']] = last_week[['store_id', 'count']].copy()
        df4['uptime_last_day'] = last_day['count'].copy()
        df4['downtime_last_week'] = (24*7) - df4['uptime_last_week']
        df4['downtime_last_day'] = 24 - df4['uptime_last_day']
        df4['uptime_last_hour'] = last_hour['uptime_last_hour'].copy()
        df4['downtime_last_hour'] = 60 - last_hour['uptime_last_hour']
        df4.to_csv(os.path.dirname( __file__ ) + '/GeneratedReports/'+ str(self.request.id) + '.csv')
    except:
        app.control.revoke(self.request.id, terminate=True, signal='SIGKILL')
    
    
    

@shared_task()
def StorePoll():
    logger.info('############################### '+ str(os.getpid()) + ' ###############################')
    logger.info(datetime.now(timezone("Asia/Kolkata")).strftime('%d-%b-%y %H:%M:%S.%f'))
    logger.info("Store Polling Data Entry Service Has Begun...")
    try:
        SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = Credentials.from_service_account_file(str(os.path.dirname(os.path.realpath(__file__)))+"/service-account.json", scopes=SCOPES)
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        request = service.files().get_media(fileId="1UIx1hVJ7qt_6oQoGZgb8B3P2vd1FD025")
        file = BytesIO()
        downloader = MediaIoBaseDownload(file,request)
        done = False
        while done is False: _,done = downloader.next_chunk()
        file.seek(0)
        ####################
        df = read_csv(file)
        ####################
        logger.info("CSV File Download Completed From Google Drive...")
        list = []
        
        if StoreStatus.objects.all().last().timestamp_utc == df['timestamp_utc'].iloc[-1]:
            logger.info("Transfer To DataBase Incomplete...")
            print(datetime.now(timezone("Asia/Kolkata")).strftime('%d-%b-%y %H:%M:%S.%f'), end = '\n\n')
        
        else:
            for ind in df.index:
                temp = StoreStatus(store_id=df['store_id'][ind], timestamp_utc=df['timestamp_utc'][ind], status=df['status'][ind])
                list.append(temp)
                
            StoreStatus.objects.bulk_create(list)
            logger.info("Transfer To DataBase Is Complete...")
            logger.info(datetime.now(timezone("Asia/Kolkata")).strftime('%d-%b-%y %H:%M:%S.%f'), end = '\n\n')
            
            queryset1 = StoreStatus.objects.all()
            fields = ['store_id', 'timestamp_utc', 'status']
            data = queryset1.values(*fields)
            df = pd.DataFrame(data, columns=fields)
            df.to_csv(os.path.dirname( __file__ ) +'/GeneratedReports/PolledS.csv')
            
            queryset2 = BusinessHours.objects.all()
            fields = ['store_id', 'day', 'start_time_local', 'end_time_local']
            data = queryset2.values(*fields)
            df = pd.DataFrame(data, columns=fields)
            df.to_csv(os.path.dirname( __file__ ) +'/GeneratedReports/BusinessH.csv')
        
            queryset3 = StoreTimezone.objects.all()
            fields = ['store_id', 'timezone_str']
            data = queryset3.values(*fields)
            df = pd.DataFrame(data, columns=fields)
            df.to_csv(os.path.dirname( __file__ ) +'/GeneratedReports/TimeZoneS.csv')
            
    except:
        logger.info("Service Has Been Cancelled Due To Google OAuth Failure...")
        logger.info(datetime.now(timezone("Asia/Kolkata")).strftime('%d-%b-%y %H:%M:%S.%f'), end = '\n\n')