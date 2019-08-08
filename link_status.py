import config as cfg
import pymysql
import requests
import sys
from ThreadPool import ThreadPool

log_filename = "url_status.log"
timeout = 0.01


def check_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        }
        r = requests.get(
            url, stream=True, allow_redirects=True, headers=headers, timeout=timeout
        )
        output_status(url, r.status_code)
    except Exception as ex:
        output_status(url, 0, str(ex))


def get_externallinks(cursor):
    # Pull links from the wiki database
    try:
        sql = "SELECT DISTINCT `el_to` FROM externallinks"
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as ex:
        sys.exit("Error retrieving external links: " + str(ex))


def get_wikidb():
    try:
        return pymysql.connect(
            host=cfg.mysql["server"],
            db=cfg.mysql["db"],
            port=int(cfg.mysql["port"]),
            user=cfg.mysql["user"],
            password=cfg.mysql["pass"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    except:
        sys.exit(
            "Error connecting to database - verify connection information in configuration"
        )


def output_status(url, status, error=""):
    with open(log_filename, "a") as f:
        if error == "":
            result = "%s\t%s" % (status, url)
        else:
            result = "%s\t%s\t%s" % (status, url, error)

        print(result, file=f)


mysqldb = get_wikidb()
pool = ThreadPool(8)
with mysqldb.cursor() as cursor:
    externallinks = get_externallinks(cursor)

    with open(log_filename, "w") as f:
        print("Status\tURL\tError", file=f)

    for link in externallinks:
        url = link["el_to"].decode("utf-8").strip()
        pool.add_task(check_url, (url))

pool.wait_completion()
mysqldb.close()
