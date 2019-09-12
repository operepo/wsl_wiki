# wsl_wiki

Code to help convert the WA State Library ILS Reentry (https://wiki.sos.wa.gov/ILSRe-entry/)
wiki resources to run offline

# Purpose

The Washington State Library has put together a great wiki full or resources that can be used
for reentry by inmates. Due to a lack of internet access by inmates, this is an attempt to
automate the conversion of the wiki to run fully offline in a prison environment.

# Current Status

Tested with MediaWiki 1.24. MediaWiki 1.3+ has known changes to the database structure that
this script is not currently set up to handle.

# Features

- Downloads PDF files that are linked externally and makes a copy on the local server.
- Pulls external HTML pages and renders them as a PDF file on the local server.
- Updates links in the local database to point to offline files.
- Saves changed files only, saving processing time
- Multithreaded (default 10 threads) - 1200 links downloading/converted in 12 minutes vs 3 hours

# Environment

- Windows - running under XAMPP with MediaWiki 1.4. Good for putting on WSL laptops.
- Planned (not available yet) - Run as a docker container to become part of the OPE project.

<!---
May include later if entire ZIP is made public
# Windows Setup

1. Create base XAMPP folder (recommend in root, i.e. C:\XAMPP) and unzip reentry_wiki_xampp.zip into folder.
2. Using PowerShell as Adminstrator (replace "C:\XAMPP" with folder created in step 1):
   - Install Apache service using `C:\XAMPP\apache\apache_installservice.bat`
   - Install MySQL service using `C:\XAMPP\mysql\bin\mysqld --install`
3. Ensure services are installed and running
4. Navigate to http://localhost

# Securing Local Wiki Installation

For offline use in secure facilities, it is HIGHLY recommended that the XAMPP installation be secured from user accounts. Suggested actions include using a limited service account for maintaing the XAMPP installation and running the Apache/MySQL services and setting security permissions to only allow access to the C:\XAMPP folder by this service account.
-->

# Development / Updates

To run the python script which will download/fix links, you need python 3.6.? installed (python.org). Look at modules.txt in this folder for the modules you need to install. In addition, you will need a local copy of your own MediaWiki installation.

- Install python modules (e.g. pip install pdfkit)
- Rename `config-dist.py` to `config.py` and modify with local configuration
- Using PowerShell (may require _as Administrator_), type the command `python find_links.py`
