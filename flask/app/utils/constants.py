SELECTOR_ID = 'unianalytics'
Selectors = {
    "cellMapping": f"{SELECTOR_ID}_cell_mapping",
    "notebookId": f"{SELECTOR_ID}_notebook_id"
}

MAX_PAYLOAD_SIZE = 1048576 # 1*1024*1024 = 1MB in bytes

from datetime import timedelta
DASHBOARD_REFRESH_RATE_LIMIT_DURATION = timedelta(seconds=5)