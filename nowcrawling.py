#!/usr/bin/env python3
import os
import time
import sys

__author__ = 'jota'

import urllib.request
import urllib.parse
from optparse import OptionParser, OptionGroup
import re

GOOGLE_SEARCH_URL = "http://google.com/search?%s"
GOOGLE_SEARCH_REGEX = 'a href="[^\/]*\/\/(?!webcache).*?"'
GOOGLE_USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
##    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
## GOOGLE_SEARCH_REGEX = 'href="\/url\?q=[^\/]*\/\/(?!webcache).*?&amp'
SMART_FILE_SEARCH = " intitle:index of "
GOOGLE_NUM_RESULTS = 100
FILE_REGEX = '(href=[^<>]*tagholder[^<>]*\.(?:typeholder))|((?:ftp|http|https):\/\/[^<>]*tagholder[^<>]*\.(?:typeholder))'
YES = ['yes', 'y', 'ye']
URL_TIMEOUT = 7

MAX_FILE_SIZE = 2**50

def get_timestamp():
    return time.strftime('%Y/%m/%d %H:%M:%S')
class Logger:

    shell_mod = {
        '':'',
       'PURPLE' : '\033[95m',
       'CYAN' : '\033[96m',
       'DARKCYAN' : '\033[36m',
       'BLUE' : '\033[94m',
       'GREEN' : '\033[92m',
       'YELLOW' : '\033[93m',
       'RED' : '\033[91m',
       'BOLD' : '\033[1m',
       'UNDERLINE' : '\033[4m',
       'RESET' : '\033[0m'
    }

    def log ( self, message, is_bold=False, color='', log_time=True):
        prefix = ''
        suffix = ''

        if log_time:
            prefix += '[{:s}] '.format(get_timestamp())

        if os.name == 'posix':
            if is_bold:
                prefix += self.shell_mod['BOLD']
            prefix += self.shell_mod[color.upper()]

            suffix = self.shell_mod['RESET']

        message = prefix + message + suffix
        print ( message )
        sys.stdout.flush()


    def error(self, err):
        self.log(err, True, 'RED')

    def fatal_error(self, err):
        self.error(err)
        exit()

def doVerbose(f, verbose=False):
    if verbose:
        f()

def crawlGoogle(numres, start, hint, smart):
    query = urllib.parse.urlencode({'num': numres, 'q': (hint+SMART_FILE_SEARCH if smart and SMART_FILE_SEARCH not in hint else hint), "start": start})
    url = GOOGLE_SEARCH_URL % query
    headers = {'User-Agent': GOOGLE_USER_AGENT, }
    request = urllib.request.Request(url, None, headers)
    response = urllib.request.urlopen(request)
    data = str(response.read())
    p = re.compile(GOOGLE_SEARCH_REGEX, re.IGNORECASE)

    ##return list(set(x.replace('href="/url?q=', '').replace('HREF="/url?q=', '').replace('"', '').replace('&amp', '') for x in p.findall(data)))
    return list(set(x.replace('a href=', '').replace('a HREF=', '').replace('"', '').replace('A HREF=', '') for x in p.findall(data)))

def getTagsRe(tags):
    tagslist = tags.split()
    tagsre = "[^<>]*".join(tagslist)
    ##print(tagsre)
    return tagsre

def getTypesRe(types):
    return types.replace(' ', '|')

def crawlURLs(crawlurl, tags, regex2, types, getfiles, verbose):
    url = crawlurl
    headers = {'User-Agent': GOOGLE_USER_AGENT, }

    request = urllib.request.Request(url, None, headers)
    try:
        response = urllib.request.urlopen(request,timeout=URL_TIMEOUT)
        data = str(response.read())
    except KeyboardInterrupt:
        Logger().fatal_error('Interrupted. Exiting...')
        return []
    except:
        doVerbose(lambda: Logger().log('URL '+crawlurl+' not available', True, 'RED'), verbose)
        return []

    if (getfiles):
        if not tags and not regex2:
            regex = FILE_REGEX.replace('tagholder', '').replace('typeholder', getTypesRe(types))
        elif (tags is not None):
            regex = FILE_REGEX.replace('tagholder', getTagsRe(tags)).replace('typeholder', getTypesRe(types))
        else:
            regex = FILE_REGEX.replace('tagholder', regex2).replace('typeholder', getTypesRe(types))
    else:
        regex = regex2

    p = re.compile(regex, re.IGNORECASE)

    tuples = p.findall(data)

    if (len(tuples) < 1):
        return []

    if (getfiles):
        tuples = [j[i] for j in tuples for i in range(len(j)) if '.' in j[i]]
        prettyurls = list(x.replace('href=', '').replace('HREF=', '').replace('"', '').replace('\\', '') for x in tuples)
        prettyurls = list(crawlurl+x if "://" not in x else x for x in prettyurls)
    else:
        ## RETURN EVERYTHING IF TUPLES
        if (isinstance(tuples[0],tuple)):
            prettyurls = list(j[i] for j in tuples for i in range(len(j)))
        else:
            prettyurls = list(x for x in tuples)

    return prettyurls

def parse_input():
    parser = OptionParser()
    parser.add_option('-f', '--files', help='Crawl for files', action="store_true", dest="getfiles")
    parser.add_option('-c', '--content', help='Crawl for content (words, strings, pages, regexes)', action="store_false", dest="getfiles")
    parser.add_option('-k', '--keywords', help='(Required) A quoted list of words separated by spaces which will be the search terms of the crawler', dest='keywords', type='string')
    parser.add_option('-v', '--verbose', help='Display all error/warning/info messages', action="store_true", dest="verbose",default=False)

    filesgroup = OptionGroup(parser, "Files (-f) Crawler Arguments")
    filesgroup.add_option('-a', '--ask', help='Ask before downloading', action="store_true", dest="ask", default=False)
    filesgroup.add_option('-l', '--limit', help='File size limit in bytes separated by a hyphen (example: 500-1200 for files between 500 and 1200 bytes, -500 for files smaller than 500 bytes, 500- for files larger than 500 bytes) (Default: None)', dest="limit", type='string', default=None)
    filesgroup.add_option('-n', '--number', help='Number of files to download until crawler stops (Default: Max)', dest="maxfiles", type='int', default=None)
    filesgroup.add_option('-e', '--extensions', help='A quoted list of file extensions separated by spaces. Default: all', dest='extensions', type='string', default='[a-zA-Z0-9]+')
    filesgroup.add_option('-s', '--smart', help='Smart file search, will highly reduce the crawling time but might not crawl all the results. Basically the same as appending \'intitle: index of\' to your keywords.', action="store_true", dest="smart", default=False)

    filenamegroup = OptionGroup(parser, "File Names Options", "You can only pick one."" If none are picked, EVERY file matching the specified extension will be downloaded")
    filenamegroup.add_option('-t', '--tags', help='A quoted list of words separated by spaces that must be present in the file name that you\'re crawling for', dest='tags', type='string')
    filenamegroup.add_option('-r', '--regex', help='Instead of tags you can just specify a regex for the file name you\'re looking for', dest='regex', type='string')
    ##TODO FIXME -R STILL NEEDS TESTING!
    ##TODO FIXME MAIS UM ARGUMENTO COM UM SITE ESPECIFICO PARA NAO TER DE IR AO GOOGLE
    parser.add_option_group(filesgroup)
    parser.add_option_group(filenamegroup)

    contentgroup = OptionGroup(parser, "Content (-c) Crawler Arguments")
    contentgroup.add_option('-m', '--match', help='(Required) A regex that will match the content you are crawling for', dest='regex', type='string')

    parser.add_option_group(contentgroup)

    (options, args) = parser.parse_args()

    if (options.getfiles is None):
        parser.error('You must specify the crawler type: -f for files or -c for content')
    if (options.getfiles is True and options.keywords is None):
        parser.error('You must specify keywords when crawling for files.')
    if (options.getfiles is False and options.keywords is None):
        parser.error('You must specify keywords when crawling for content.')
    if (options.getfiles is True and (options.tags is not None and options.regex is not None)):
        parser.error('You can\'t pick both file name search options: -t or -r')
    if (options.getfiles is True and options.limit is not None and '-' not in options.limit):
        parser.error('Limits must be separated by a hyphen.')
    if (options.getfiles is False and options.regex is None):
        parser.error('You must specify a matching regex (-m) when crawling for content.')
    ## FIXME FALTA TANTO CHECK AI JASUS, TIPO VER SE O GAJO NAO METE -A SEM METER -F ENTRE OUTROS AI JASUS

    return options.getfiles, options.keywords, options.extensions, options.smart, options.tags, options.regex, options.ask, options.limit, options.maxfiles, options.verbose

def getMinMaxSizeFromLimit(limit):
    if limit:
        minsize, maxsize = limit.split('-')
        if not minsize:
            minsize = '0'
        if not maxsize:
            maxsize = str(MAX_FILE_SIZE)

        if maxsize and minsize and int(maxsize) < int(minsize):
            Logger().log("You are dumb, but it's fine, I will swap limits", color='RED')
            return int(maxsize),int(minsize)
    else:
        return 0,MAX_FILE_SIZE

#From http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)

def sizeToStr(filesize):
    return sizeof_fmt(filesize)

"""
    Download files from downloadurls, respecting conditions, updating file counts and printing info to user
"""
def downloadFiles(downloaded, downloadurls, ask, searchurl, maxfiles, limit,minsize, maxsize,verbose):
    for file in downloadurls:

        # Check if we've reached the maximum number of files
        if maxfiles and downloaded >= maxfiles:
            doVerbose(lambda: Logger().log('All files have been downloaded. Exiting...', True, 'GREEN'), verbose)
            exit()

        filename = file.split('/')[-1]
        try:
            meta = urllib.request.urlopen(file).info()
            filesize = int(meta.get_all("Content-Length")[0])
            # Check filesize
            if limit and not (minsize <= filesize <= maxsize):
                doVerbose(lambda: Logger().log(
                    'Skipping file {:s} because {:s} is off limits.'.format(filename, sizeToStr(filesize)),
                    color='YELLOW'), verbose)
                continue

            # Check with user
            if ask:
                Logger().log(
                    'Download file {:s} of size {:s} from {:s}? [y/n]: '.format(filename, sizeToStr(filesize), file),
                    color='DARKCYAN')
                choice = input().lower()
                if choice not in YES:
                    continue
            doVerbose(lambda: Logger().log('Downloading file {:s} of size {:s}'.format(filename, sizeToStr(filesize)),
                                           color='GREEN'), verbose)

            # Get the file
            urllib.request.urlretrieve(file, filename)

            doVerbose(lambda: Logger().log('Done downloading file {:s}'.format(filename),color='GREEN'), verbose)
            downloaded += 1
        except KeyboardInterrupt:
            Logger().fatal_error('Interrupted. Exiting...')
        except:
            doVerbose(lambda: Logger().log('File ' + file + ' from ' + searchurl + ' not available', True, 'RED'),
                      verbose)
            continue

    return downloaded

def crawl(getfiles, keywords, extensions, smart, tags, regex, ask, limit, maxfiles, verbose):
    downloaded = 0
    start = 0
    minsize,maxsize = getMinMaxSizeFromLimit(limit)

    while True:
        try:
            doVerbose(lambda: Logger().log('Fetching {:d} results.'.format(GOOGLE_NUM_RESULTS)), verbose)
            googleurls = crawlGoogle(GOOGLE_NUM_RESULTS, start, keywords, smart)
            doVerbose(lambda: Logger().log('Fetched {:d} results.'.format(len(googleurls))),verbose)

            for searchurl in googleurls:
                doVerbose(lambda: Logger().log('Crawling into '+searchurl+' ...'), verbose)

                downloadurls = crawlURLs(searchurl, tags, regex, extensions, getfiles, verbose)
                urllib.request.urlcleanup()
                if not downloadurls:
                    doVerbose(lambda: Logger().log('No results in '+searchurl), verbose)
                else:
                    # Got results
                    if getfiles:
                        downloaded += downloadFiles(downloaded, downloadurls, ask, searchurl, maxfiles, limit,minsize, maxsize,verbose)
                    else:
                        for match in downloadurls:
                            Logger().log(match,color='GREEN')

            # If google gave us less results than we asked for, then we've reached the end
            if len(googleurls) < GOOGLE_NUM_RESULTS:
                Logger().log('No more results. Exiting.', True, 'GREEN')
                break
            else:
                start+=len(googleurls)
        except KeyboardInterrupt:
            Logger().fatal_error('Interrupted. Exiting...')

try:
    #crawl(True, "pink floyd", "mp3", True, None, None, False, None, None, True)
    crawl(*parse_input())
except KeyboardInterrupt:
    Logger().fatal_error('Interrupted. Exiting...')

