import os
import sys
import json
import requests
import hashlib
import shutil
import re
import pdfkit
import platform
import sqlitedict
import pymysql
import config as cfg
from ThreadPool import ThreadPool

# Global variables
dl_path = ""
# thread_pool = ThreadPool(4)
timeout = 30.00  # Allows 30 seconds for page load/timeout


def download_file(url, local_path):
    try:
        print("Downloading File: %s to %s." % (url, local_path))
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        }
        r = requests.get(
            url, stream=True, allow_redirects=True, headers=headers, timeout=timeout
        )
        if r.status_code == 404:
            print(" ---- 404 URL Not Found: " + url)
            with open("404errors.log", "a") as f:
                print(url, file=f)
            return None
        content_type = r.headers.get("content-type")
        extension = None
        if "text/html" in content_type:
            # Use pdfkit to get a pdf version of the page
            options = {"log-level": "error"}
            pdfkit.from_url(url, local_path, options=options)
            extension = ".pdf"
        elif "/pdf" in content_type:
            extension = ".pdf"
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive empty chunks
                        f.write(chunk)
                        # f.flush()
        return extension
    except requests.exceptions.Timeout as ex:
        print("Timeout downloading file: %s | %s" % (url, str(ex)))
    except Exception as ex:
        print("Error downloading file: " + str(ex))


def find_links():
    print("******* Converting links to offline *******")

    # Initilize
    set_pdfkit_config()
    set_dl_path()

    # Local db connection with list of links
    linkdb = get_linkdb()

    # Connect to mysql database to find links
    mysqldb = get_wikidb()

    with mysqldb.cursor() as cursor:
        externallinks = get_externallinks(cursor)

        # iterate through externallinks, add to linkdb if new
        for link in externallinks:
            k = link["el_to"]
            if k not in linkdb:
                print("Found new link... " + str(k))
                linkdb[k] = ""

        linkdb.commit()

        # See if each file exists in the dl_path
        for key, value in linkdb.iteritems():
            k_url = key.decode("utf-8")
            v = value

            try:
                if k_url == "":
                    print("URL Missing: %s." % k_url)
                    continue

                if len(v) > 10:
                    print("File already downloaded: %s." % k_url)
                    continue

                tmp_file = os.path.join(dl_path, "tmp_dl")

                extension = download_file(k_url, tmp_file)
                if extension is None:
                    # Unable to dl file, move to next one
                    continue

                # Calculate tmp file hash
                h = hashlib.sha1()

                with open(tmp_file, "rb") as f:
                    chunk = f.read(65535)
                    if not chunk:
                        continue
                    h.update(chunk)
                hash = h.hexdigest()
                final_path = os.path.join(dl_path, hash + extension)

                shutil.copyfile(tmp_file, final_path)

                if hash != "":
                    linkdb[key] = hash + extension

                # Update mysql database with new link
                new_url = cfg.wiki["url"] + "dl_files/" + hash + extension

                print("File download complete: %s to %s" % (k_url, new_url))

                sql = "UPDATE text SET old_text=REPLACE(old_text, %s, %s);"
                cursor.execute(sql, (k_url, new_url))
                mysqldb.commit()
            except Exception as ex:
                print("Error pulling file: " + str(ex))
                continue

            linkdb.commit()

    # thread_pool.wait_completion()
    print("Files downloaded to " + dl_path)
    purge_pages()
    linkdb.commit()
    linkdb.close()
    mysqldb.close()


def get_app_path():
    return os.path.abspath(os.path.dirname(__file__))


def get_externallinks(cursor):
    # Pull links from the wiki database
    try:
        sql = "SELECT * FROM externallinks"
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as ex:
        sys.exit("Error retrieving external links: " + str(ex))


def get_file_name_from_cd_header(cd_header):
    # Pull the filename from the content-disposition header
    if not cd_header:
        return ""
    fname = re.findall("filename=(.+)", cd_header)
    if len(fname) == 0:
        return ""
    return fname[0]


def get_linkdb():
    try:
        return sqlitedict.SqliteDict(
            get_app_path() + "/links.db",
            encode=json.dumps,
            decode=json.loads,
            autocommit=False,
        )
    except Exception as ex:
        sys.exit("Error initilizing linkdb: " + str(ex))


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


def purge_pages():
    # Purge the page to make it refresh from the database
    try:
        s = requests.Session()
        url = cfg.wiki["url"] + "api.php"
        params = {"action": "purge", "generator": "allpages", "forcelinkupdate": True}
        s.post(url, params=params)
        print("Pages purged")
    except:
        pass


def set_dl_path():
    global dl_path

    wiki_path = cfg.wiki["path"]

    if not os.path.exists(wiki_path):
        sys.exit("Wiki path does not exist - verify " + wiki_path)

    dl_path = os.path.join(wiki_path, "dl_files")

    # Create download folder if not exists
    try:
        os.makedirs(dl_path)
    except:
        pass


def set_pdfkit_config():
    # set path to local copy of wkhtmltopdf.exe if on Windows machine
    if platform.system() == "Windows":
        pdfkit.configuration(
            wkhtmltopdf=os.path.join(get_app_path(), "wkhtmltopdf.exe")
        )


# Call main program
# http://localhost:8080/mediawiki/index.php/Benton_County
# http://example.org/wiki/index.php?title=Main_Page&action=purge
# c:\xampp\php\php.exe purgePage.php

find_links()
