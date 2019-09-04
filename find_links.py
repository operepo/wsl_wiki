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
thread_pool = ThreadPool(10)
file_cleanup = []
max_items = 0        # Max number of entries to process, 0 for unlimited -- leave at 0 except for testing

def main():
    print("******* Converting links to offline *******")

    # Initilize globals
    set_pdfkit_config()
    set_dl_path()
    linkdb = get_linkdb()
    wikidb = get_wikidb()

    externallinks = get_externallinks(wikidb.cursor())

    # iterate through externallinks, add to linkdb if new
    for link in externallinks:
        k = link["el_to"].decode("utf8")
        if k not in linkdb:
            print("Found new link... " + k)
            linkdb[k] = ""

    linkdb.commit()

    # See if each file exists in the dl_path
    i = 0
    for key, value in linkdb.iteritems():
        if i > max_items:
            break
        else:
            if max_items > 0:
                i += 1

        if key == "":
            print("URL Missing: %s." % key)
            continue

        thread_pool.add_task(get_docs, key, value)

    # Wait for all threads to finish before clean-up
    thread_pool.wait_completion()

    purge_pages()
    linkdb.commit()
    cleanup_files()
    
    linkdb.close()
    wikidb.close()
    print("Complete\nErrors have been logged in errors.log\nFiles downloaded to " + dl_path)


def cleanup_files():
    for item in file_cleanup:
        try:
            # Check if file still being referred to in linkdb
            if not item in linkdb.values():
                os.remove(dl_path + item + ".pdf")
        except:
            # File not found
            pass    


def download_file(url, old_hash = ""):
    # Downloads file from URL, if old_hash is provided, compares file hashes to determine if the file should be re-downloaded or not
    # Returns new_hash
    global file_cleanup
    timeout = (5, 30)  # Allows 5 seconds to connect, 30 seconds for page load/timeout

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36"
        }
        r = requests.get(
            url, stream=True, allow_redirects=True, headers=headers, timeout=timeout
        )

        if r.status_code != 200:
            raise Exception("%s\t%s" % (r.status_code, url))

        h = hashlib.sha1()
        h.update(r.content)
        new_hash = h.hexdigest()

        if old_hash != new_hash:
            file_cleanup.append(old_hash)
            content_type = r.headers.get("content-type")
            if "text/html" in content_type:
                # Use pdfkit to get a pdf version of the page
                options = {
                    "log-level": "none",
                    "load-error-handling": "ignore",
                    "load-media-error-handling": "ignore",
                    "disable-external-links": False,
                    "disable-internal-links": False,
                    "disable-javascript": False,
                }
                #pdfkit.from_url(url, new_hash, options=options)
                try:
                    pdfkit.from_string(r.content.decode("utf8"), new_hash, options=options)
                except:
                    # pdfkit errors can be ignored, file is still generated
                    pass
            elif "/pdf" in content_type:
                with open(new_hash, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:  # filter out keep-alive empty chunks
                            f.write(chunk)
        return new_hash
    except Exception as ex:
        with open("errors.log", "a") as f:
            print("%s\t%s\t%s" % (r.status_code, url, str(ex)), file=f)
        return ""


def get_app_path():
    return os.path.abspath(os.path.dirname(__file__))


def get_docs(url, old_hash):
    try:
        linkdb = get_linkdb()
        mysqldb = get_wikidb()

        # Fetch and process documents
        file_hash = download_file(url, old_hash)
        linkdb[url] = file_hash
        linkdb.commit()

        if file_hash == "":
            # File not downloaded, continue to next item
            return

        final_path = os.path.join(dl_path, file_hash + ".pdf") # All files are converted to PDF

        shutil.move(file_hash, final_path)

        # Update mysql database with new link
        new_url = cfg.wiki["url"] + "dl_files/" + file_hash + ".pdf"
        
        # sql = "UPDATE text SET old_text=REPLACE(old_text, %s, %s);"  # was errantly replacing substrings
        data = [
            ("[" + url + "]", "[" + new_url + "]"),
            ("[" + url + "|", "[" + new_url + "|")
        ]
        sql = "UPDATE text SET old_text=REPLACE(old_text, %s, %s);"
        
        mysqldb.cursor().executemany(sql, data)
        
        mysqldb.commit()
        print("Downloaded %s to %s" % (url, new_url))
    except Exception as ex:
        print(str(ex))


def get_externallinks(cursor):
    # Pull links from the wiki database
    try:
        sql = "SELECT DISTINCT `el_to` FROM externallinks ORDER BY `el_to` DESC;"
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as ex:
        sys.exit("Error retrieving external links: " + str(ex))


def get_linkdb():
    try:
        # get_app_path() + "/links.db",
        return sqlitedict.SqliteDict(
            "links.db",
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
main()
