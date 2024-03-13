import os
import json
import pendulum
import pytz
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from airflow.providers.google.common.hooks.base_google import GoogleBaseHook
from google.oauth2.service_account import Credentials

from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable

from helpers import discord_alert
from wrappers.binance.binance_client import BinanceClient, BinanceKlineInterval


#TMPL_SEARCH_PATH = Variable.get('templates_path')
DAY_AGO = datetime.combine(
    datetime.today() - timedelta(days=1), datetime.min.time())

DAG_NAME = 'fetch-binance-klines-1d-data'
DAG_SCHEDULE_INTERVAL = timedelta(days=1)
DAG_ARGS = {
    'owner': 'airflow',
    'provide_context': True,
    #'trigger_rule': TriggerRule.ALL_SUCCESS,
    'on_failure_callback': discord_alert,
    'retries': 0,
    #'retry_delay': timedelta(minutes=1),
    #'sla': timedelta(hours=1),
    'depends_on_past': True,
}

PROXIES = {
    "http": Variable.get('http-proxy'),
    "https": Variable.get('http-proxy'),
}


with DAG(
    dag_id=DAG_NAME,
    default_args=DAG_ARGS,
    description='Fetch daily BTC and ETH price data from Binance',
    start_date=datetime(2020, 1, 1, tzinfo=pytz.UTC),
    schedule_interval=DAG_SCHEDULE_INTERVAL,
    catchup=True,
    #template_searchpath=TMPL_SEARCH_PATH,
    max_active_runs=1,
    tags=['fetching'],
) as dag:     

    @task(task_id="get_symbols")
    def get_symbols():
        return ['BTCUSDT', 'ETHUSDT']

    @task(task_id="fetch_data_from_binance")
    def fetch_data_from_binance(symbols, **kwargs):
        # Define time interval
        execution_date = pendulum.parse(kwargs['execution_date'])
        next_execution_date = pendulum.parse(kwargs['next_execution_date'])

        start_time = execution_date.timestamp()
        end_time = (next_execution_date - timedelta(milliseconds=1)).timestamp()

        # Define binance client
        binance_client = BinanceClient(proxies=PROXIES)

        # Get klines for the list of symbols
        klines_rows = []
        for symbol in symbols:
            klines = binance_client.get_klines(
                symbol=symbol,
                interval=BinanceKlineInterval.ONE_DAY,
                start_time=int(start_time*1000),
                end_time=int(end_time*1000),
                limit=1,
            )

            for kline in klines:
                klines_rows.append(
                    {
                        'symbol': symbol,
                        'kline_json': json.dumps(kline),
                        'load_key': execution_date.timestamp(),
                    }
                )

        return klines_rows

    @task(dag=dag, task_id="save_to_google_sheets")
    def save_to_google_sheets(data):
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

        # Get credentials from the Airflow connection
        google_sheets_api_hook = GoogleBaseHook(gcp_conn_id="google_sheets_api")
        #keyfile_dict = json.loads(google_sheets_api_hook.extras["extra__google_cloud_platform__keyfile_dict"])
        keyfile_dict = json.loads(google_sheets_api_hook._get_field('keyfile_dict'))

        print(keyfile_dict)

        # Initialize the creds variable
        creds = Credentials.from_service_account_info(info=keyfile_dict, scopes=SCOPES)

        # Create a Google Sheets API client
        service = build('sheets', 'v4', credentials=creds)

        # Specify the ID of your Google Sheet and the range
        spreadsheet_id = Variable.get('binance-klines-1d-data-spreadsheet_id')
        range_name = 'binance!A2'

        # Parse the kline_json data from the response
        parsed_data = []
        for entry in data:
            kline = json.loads(entry['kline_json'])
            parsed_data.append([
                entry['load_key'],
                entry['symbol'],
                kline['openTime'],
                kline['open'],
                kline['high'],
                kline['low'],
                kline['close'],
                kline['volume'],
                kline['closeTime'],
                kline['quoteVolume'],
                kline['numTrades'],
                kline['baseAssetVolume'],
                kline['quoteAssetVolume'],
            ])

        # Prepare the request body for appending data to the Google Sheet
        body = {
            'range': range_name,
            'majorDimension': 'ROWS',
            'values': parsed_data,
        }

        # Append the data to the Google Sheet
        sheet = service.spreadsheets()
        result = sheet.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body,
        ).execute()

        print(f"{result['updates']['updatedCells']} cells updated.")



    # temporary workaround for the bug https://github.com/apache/airflow/discussions/24463
    os.environ['NO_PROXY'] = "*"

    symbols = get_symbols()
    data = fetch_data_from_binance(symbols, execution_date="{{ execution_date }}", next_execution_date="{{ next_execution_date }}")
    save_to_google_sheets(data)

if __name__ == "__main__":
    dag.cli()
