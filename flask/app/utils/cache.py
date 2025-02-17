from flask import current_app
from app import db
from app.models.models import RefreshDashboardCache
from app.utils.constants import DASHBOARD_REFRESH_RATE_LIMIT_DURATION
from datetime import datetime
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError

# returns a boolean value that reflects if a refresh dashboard should be sent or not
def check_refresh_cache(notebook_id):
    current_time = datetime.now()

    try:

        # to avoid having concurrent requests coming from different workers/instances, lock the database row
        with db.session.begin():
            # lock the row for notebook_id if it exists or lock a non-existent row
            query = text(f"SELECT * FROM \"RefreshDashboardCache\" WHERE notebook_id = :notebook_id FOR UPDATE")
            cache_row = db.session.execute(query, {"notebook_id": notebook_id}).first()

            if cache_row is None: 
                # nothing for notebook_id in the cache, create an entry
                cache_row = RefreshDashboardCache(notebook_id=notebook_id, last_refresh_time=current_time)
                db.session.add(cache_row)
                db.session.commit()
                return True

            elif current_time - cache_row.last_refresh_time >= DASHBOARD_REFRESH_RATE_LIMIT_DURATION : 
                # enough time since last refresh, update the cached timestamp
                update_query = text(
                    "UPDATE \"RefreshDashboardCache\" "
                    "SET last_refresh_time = :last_refresh_time "
                    "WHERE notebook_id = :notebook_id"
                )
                db.session.execute(
                    update_query,
                    {"notebook_id": notebook_id, "last_refresh_time": current_time},
                )
                db.session.commit()
                return True

            else : 
                # not enough time since last refresh
                return False
        
    # used to happen with the second request trying to add a new entry while the first just did (notebook_id is a unique primary key)
    except IntegrityError:
        db.session.rollback()
        return False