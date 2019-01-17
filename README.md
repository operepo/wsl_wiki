# wsl_wiki
Code to help convert the WA State Library wiki resources to run offline

# Purpose
The Washington State Library has put together a great wiki full or resources that can be used
for reentry by inmates. Due to a lack of internet access by inmates, this is an attempt to
automate the conversion of the wiki to run fully offline in a prison environment.

# Current Status
BETA - Lots of bugs in the code, but it works as a first draft. Pulled 688 pdf files on current run.

# Features
- Pulls PDF files that are linked externally and makes a copy on the local server.
- Pulls external HTML pages and renders them as a PDF file - stores on the local server.
- Updates links in the wiki to point to local server.

# Environment
- Windows - running under XAMP with bitnami media wiki. Good for putting on WSL laptops.
- Planned (not available yet) - Run as a docker container to become part of the OPE project.

# Windows Setup
1) Install XAMP - Pull PHP 7.3.? version - https://www.apachefriends.org/download.html
    - Only need Apache/Mysql running.
2) Install Bitnami MediaWiki - Get Windows installer - https://bitnami.com/stack/mediawiki/installer
    - Install w default options
3) Stop XAMP (stop apache, mysql, close XAMP management app)
4) Copy in zipped XAMP folder (ask rpulsipher@pencol.edu - includes secrets right now).
5) Start up XAMP/Apache/Mysql
6) Navigate to http://localhost:8080/mediawiki

# Development
To run the python script which will download/fix links, you need python 3.6.? installed (python.org). Look at modules.txt in this folder for the modules you need to install.

- Install python modules (e.g.  pip install pdfkit)

- Run py file in the c:\xamp\apps\mediawiki\htdocs folder
    - cd c:\xamp\apps\mediawiki\htdocs
    - python find_links.py
    - NOTE - buts - may need to delete links.db and dl_files on subsequent runs if things quit working and let it start fresh.
