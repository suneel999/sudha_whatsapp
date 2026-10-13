from database import get_staff_request_feed, init_database

init_database()
feed = get_staff_request_feed(10)
print("feed_count", len(feed))
print("api_import_ok")
