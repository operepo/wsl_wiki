import os
import sys
import json
import requests
import hashlib
import shutil
import re
import pdfkit
import pdb

from sqlitedict import SqliteDict
import pymysql.cursors
import pymysql
import config as cfg


def get_app_path():
    return os.path.abspath(os.path.dirname(__file__))


pdf_config = pdfkit.configuration(
    wkhtmltopdf=os.path.join(get_app_path(), "wkhtmltopdf.exe")
)


def get_file_name_from_cd_header(cd_header):
    # Pull the filename from the content-disposition header
    if not cd_header:
        return ""
    fname = re.findall("filename=(.+)", cd_header)
    if len(fname) == 0:
        return ""
    return fname[0]


def download_file(url, local_path):
    local_file_name = local_path
    # print("   " + url + " -- " + local_path)
    # pdb.set_trace()

    # r = requests.head to get header information, check if changed and then pull

    r = requests.get(url, stream=True, allow_redirects=True)
    if r.status_code == 404:
        print(" ---- 404 URL Not Found: " + url)
        return None
    fname = get_file_name_from_cd_header(r.headers.get("content-disposition"))
    content_type = r.headers.get("content-type")
    extension = ".html"
    if "text/html" in content_type:
        # Use pdfkit to get a pdf version of the page
        pdfkit.from_url(url, local_path)
        # Should be a pdf now
        extension = ".pdf"
    elif "/pdf" in content_type:
        extension = ".pdf"
        # print("     " + fname + " / " + content_type)
        with open(local_file_name, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive empty chunks
                    f.write(chunk)
                    # f.flush()
    return extension


# Local db connection with list of links
linkdb = SqliteDict(
    get_app_path() + "/links.db", encode=json.dumps, decode=json.loads, autocommit=False
)

# Connect to mysql database to find links
mysqldb = pymysql.connect(
    host=cfg.mysql["server"],
    db=cfg.mysql["db"],
    port=int(cfg.mysql["port"]),
    user=cfg.mysql["user"],
    password=cfg.mysql["pass"],
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

with mysqldb.cursor() as cursor:
    # Pull links from the wiki database
    sql = "SELECT * FROM externallinks"
    cursor.execute(sql)
    rows = cursor.fetchall()

    for row in rows:
        k = row["el_to"]
        if k not in linkdb:
            print("Found new link... {0}".format(k))
            linkdb[k] = ""

        # print(" To {0} Index {1}".format(row["el_to"], row["el_index"]))
    linkdb.commit()

    # Now download each file
    base_dl_path = os.path.join(get_app_path(), "dl_files")
    try:
        os.makedirs(base_dl_path)
    except:
        pass

    link_count = len(linkdb)

    link_index = 0
    # See if each file exists in the dl_path
    for key, value in linkdb.iteritems():
        link_index += 1
        try:
            k_url = key.decode("utf-8")
            v = value
            if k_url == "":
                print("URL Missing: " + k_url)
                continue

            if len(v) > 10:
                print("File already downloaded: " + k_url)
                continue

            print("Downloading File: " + str(link_index) + "  " + k_url)
            tmp_file = os.path.join(base_dl_path, "tmp_dl")

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
            final_path = os.path.join(base_dl_path, hash + extension)
            shutil.copyfile(tmp_file, final_path)
            if hash != "":
                linkdb[key] = hash + extension

            # Update mysql database with new link
            new_url = cfg.mysql["url"] + "dl_files/" + hash + extension
            # sql = "UPDATE externallinks SET el_to=%s WHERE el_to=%s"
            # cursor.execute(sql, (new_url ,k_url))
            # mysqldb.commit()
            sql = "UPDATE text SET old_text=REPLACE(old_text, %s, %s)"
            cursor.execute(sql, (k_url, new_url))
            mysqldb.commit()
        except Exception as ex:
            print("Error pulling file: " + str(ex))
            continue

        linkdb.commit()
    print(base_dl_path)

    # Need to get a list of pages and purge them all so wiki text refreshes
    sql = "SELECT page_title FROM page"
    cursor.execute(sql)
    rows = cursor.fetchall()

    for row in rows:
        title = row["page_title"].decode("utf-8")
        url = cfg.mysql["url"] + "index.php/" + title
        params = dict()
        params["action"] = "purge"
        # Purge the page to make it refresh from the database
        r = requests.post(url, params=params, allow_redirects=True)
        print("Purging Page: " + title + " - " + url + " " + str(r.status_code))

    # http://localhost:8080/mediawiki/index.php/Benton_County
    # http://example.org/wiki/index.php?title=Main_Page&action=purge
    # c:\xampp\php\php.exe purgePage.php


linkdb.commit()
linkdb.close()
mysqldb.close()
