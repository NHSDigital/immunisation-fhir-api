"""A simple global HTTP requests session. It will retry three times with backoff for any 502 errors of any HTTP method.
This is due to a known issue with the Apigee -> AWS APIGW backend where intermittent 502 errors can be seen when
initially ramping up traffic"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(total=3, allowed_methods=None, status_forcelist=[502], backoff_factor=1)
http_requests_session = requests.Session()
http_requests_session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
