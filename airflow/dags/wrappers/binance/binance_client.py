from enum import Enum
from requests import Request, Session, Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any, List
from tenacity import retry, stop_after_attempt
import logging
import time


class BinanceKlineInterval(str, Enum):
    ONE_MINUTE = '1m'
    THREE_MINUTES = '3m'
    FIVE_MINUTES = '5m'
    FIFTEEN_MINUTES = '15m'
    THIRTY_MINUTES = '30m'
    ONE_HOUR = '1h'
    TWO_HOURS = '2h'
    FOUR_HOURS = '4h'
    SIX_HOURS = '6h'
    EIGHT_HOURS = '8h'
    TWELVE_HOURS = '12h'
    ONE_DAY = '1d'
    THREE_DAYS = '3d'
    ONE_WEEK = '1w'
    ONE_MONTH = '1M'


class BinanceClient:
    _ENDPOINT = 'https://api.binance.com/api/v3/'
    _USED_WEIGHT_LIMIT = 429

    def __init__(self, api_key: str=None, api_secret: str=None, proxies: Dict=None) -> None:
        self._session = Session()
        self._api_key = api_key
        self._api_secret = api_secret
        self._proxies = proxies

        retry = Retry(connect=5, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('GET', path, params=params)

    def _post(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('POST', path, json=params)

    def _delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('DELETE', path, json=params)

    #@retry(stop=stop_after_attempt(3))
    def _request(self, method: str, path: str, params={}, **kwargs) -> Any:
        uri = path
        data_json = ''

        if method in ['GET', 'DELETE']:
            if params:
                strl = []
                for key in params:
                    if params[key]:
                        strl.append('{}={}'.format(key, params[key]))
                data_json += '&'.join(strl)
                uri += f'?{data_json}' if len(data_json) else ''

        url = f'{self._ENDPOINT}{uri}'
        request = Request(method, url, **kwargs)

        #self._sign_request(request)

        response: Response = self._session.send(request.prepare(), proxies=self._proxies)

        # check used weight
        current_used_weight = 0 if response.headers.get('x-mbx-used-weight') is None else int(response.headers.get('x-mbx-used-weight'))
        if current_used_weight >= self._USED_WEIGHT_LIMIT:
            retry_after = response.headers.get('Retry-After')
            logging.info(f'We hits to the API requests limit, to avoid ban, we have to wait for {retry_after} seconds.')
            time.sleep(retry_after)

        return self._check_response(response)

    @staticmethod
    def _check_response(response: Response) -> dict:
        if f'{response.status_code}'[0] == '2':
            try:
                data = response.json()
            except ValueError:
                raise Exception(response.content)
            else:
                return data
        else:
            logging.info(response.headers)
            raise Exception(f'{response.status_code}: {response.text}')

    def get_symbols(self, permissions: Optional[str] = None) -> List[dict]:
        data = self._get('exchangeInfo', {'permissions': permissions})
        return data['symbols']

    def get_klines(self, symbol: str = None, interval: BinanceKlineInterval = None,
            start_time: Optional[float] = None, end_time: Optional[float] = None, limit: Optional[int] = 500) -> List[dict]:
        """Get prices
        
        Args:
            symbol (str): symbol information
                BTCBNB
            interval (str): Kline/Candlestick chart intervals 
                s-> seconds; m -> minutes; h -> hours; d -> days; w -> weeks; M -> months
            start_time (float):
                dt = datetime.datetime(2022, 4, 21, 23, 0, 0, 0)
                dt.timestamp()*1000
                If startTime and endTime are not sent, the most recent klines are returned.
            end_time (float):
                dt = datetime.datetime(2022, 4, 21, 23, 59, 59, 999)
                dt.timestamp()*1000
                If startTime and endTime are not sent, the most recent klines are returned.
            limit (int): 
                Default 500; max 1000.
    
        Returns:
            array of dict
        """
        data = self._get(f'klines',
            {'symbol': symbol, 'interval': interval, 'limit': limit, 'startTime': start_time, 'endTime': end_time})

        return [{
            "openTime": d[0],
            "open": d[1],
            "high": d[2],
            "low": d[3],
            "close": d[4],
            "volume": d[5],
            "closeTime": d[6],
            "quoteVolume": d[7],
            "numTrades": d[8],
            "baseAssetVolume": d[9],
            "quoteAssetVolume": d[10],
        } for d in data]

    def test(self):
        pass
