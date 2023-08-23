#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import urllib.parse
from datetime import datetime as dt

from sharedutils import gcount
from sharedutils import openjson
from sharedutils import postcount
from sharedutils import hostcount
from sharedutils import groupcount
from sharedutils import postssince
from sharedutils import parsercount
from sharedutils import onlinecount
from sharedutils import postslast24h
from sharedutils import version2count
from sharedutils import poststhisyear
from sharedutils import currentmonthstr
from sharedutils import monthlypostcount
#from sharedutils import headlesscount
#from sharedutils import countcaptchahosts
from sharedutils import stdlog, dbglog, errlog, honk
from plotting import trend_posts_per_day, plot_posts_by_group, pie_posts_by_group, plot_posts_by_group_past_7_days

# For RSS Feed
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
import xml.sax.saxutils as saxutils
import uuid

# To create a GUID for RSS Feed 
def md5GUID(input_string):
    md5_hash = hashlib.md5(input_string.encode('utf-8')).hexdigest()
    return md5_hash

def suffix(d):
    return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

def custom_strftime(fmt, t):
    return t.strftime(fmt).replace('{S}', str(t.day) + suffix(t.day))

friendly_tz = custom_strftime('%B {S}, %Y', dt.now()).lower()

def writeline(file, line):
    '''write line to file'''
    with open(file, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
        f.close()

def groupreport():
    '''
    create a list with number of posts per unique group
    '''
    stdlog('generating group report')
    posts = openjson('posts.json')
    # count the number of posts by group_name within posts.json
    group_counts = gcount(posts)
    # sort the group_counts - descending
    sorted_group_counts = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)
    stdlog('group report generated with %d groups' % len(sorted_group_counts))
    return sorted_group_counts

def mainpage():
    '''
    main markdown report generator - used with github pages
    '''
    stdlog('generating main page')
    uptime_sheet = 'docs/README.md'
    with open(uptime_sheet, 'w', encoding='utf-8') as f:
        f.close()
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, '## summary')
    writeline(uptime_sheet, '_' + friendly_tz + '_')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, 'currently tracking `' + str(groupcount()) + '` groups across `' + str(hostcount()) + '` relays & mirrors - _`' + str(onlinecount()) + '` currently online_')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, '⏲ there have been `' + str(postslast24h()) + '` posts within the `last 24 hours`')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, '🦈 there have been `' + str(monthlypostcount()) + '` posts within the `month of ' + currentmonthstr() + '`')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, '🪐 there have been `' + str(postssince(90)) + '` posts within the `last 90 days`')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, '🏚 there have been `' + str(poststhisyear()) + '` posts within the `year of ' + str(dt.now().year) + '`')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, '🦕 there have been `' + str(postcount()) + '` posts `since the dawn of ransomwatch`')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, 'there are `' + str(parsercount()) + '` custom parsers indexing posts')
    #writeline(uptime_sheet, 'there are `' + str(parsercount()) + '` active parsers, `' + str(headlesscount()) + '` of which using headless browsers - _`' + str(countcaptchahosts()) + '` groups have recently introduced captchas_')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, '_`' + str(version2count()) + '` sites using v2 onion services are no longer indexed - [support.torproject.org](https://support.torproject.org/onionservices/v2-deprecation/)_')
    writeline(uptime_sheet, '')
    writeline(uptime_sheet, '> see the project [README](https://github.com/joshhighet/ransomwatch#ransomwatch--) for backend technicals')

def indexpage():
    index_sheet = 'docs/INDEX.md'
    with open(index_sheet, 'w', encoding='utf-8') as f:
        f.close()
    groups = openjson('groups.json')
    writeline(index_sheet, '# 📚 index')
    writeline(index_sheet, '')
    header = '| group | title | status | last seen | location |'
    writeline(index_sheet, header)
    writeline(index_sheet, '|---|---|---|---|---|')
    for group in groups:
        stdlog('generating group report for ' + group['name'])
        for host in group['locations']:
            stdlog('generating host report for ' + host['fqdn'])
            if host['available'] is True:
                #statusemoji = '⬆️ 🟢'
                statusemoji = '🟢'
                lastseen = ''
            elif host['available'] is False:
                # iso timestamp converted to yyyy/mm/dd
                lastseen = host['lastscrape'].split(' ')[0]
                #statusemoji = '⬇️ 🔴'
                statusemoji = '🔴'
            if host['title'] is not None:
                title = host['title'].replace('|', '-')
            else:
                title = ''
            line = '| [' + group['name'] + '](https://ransomwatch.telemetry.ltd/#/profiles?id=' + group['name'] + ') | ' + title + ' | ' + statusemoji + ' | ' + lastseen + ' | ' + host['fqdn'] + ' |'
            writeline(index_sheet, line)

def statspage():
    '''
    create a stats page in markdown containing the matplotlib graphs
    '''
    stdlog('generating stats page')
    statspage = 'docs/stats.md'
    # delete contents of file
    with open(statspage, 'w', encoding='utf-8') as f:
        f.close()
    writeline(statspage, '# 📊 stats')
    writeline(statspage, '')
    writeline(statspage, '_timestamp association commenced october 21"_')
    writeline(statspage, '')
    writeline(statspage, '| ![](graphs/postsbygroup7days.png) | ![](graphs/postsbyday.png) |')
    writeline(statspage, '|---|---|')
    writeline(statspage, '![](graphs/postsbygroup.png) | ![](graphs/grouppie.png) |')
    writeline(statspage, '')
    stdlog('stats page generated')

def recentposts(top):
    '''
    create a list the last X posts (most recent)
    '''
    stdlog('finding recent posts')
    posts = openjson('posts.json')
    # sort the posts by timestamp - descending
    sorted_posts = sorted(posts, key=lambda x: x['discovered'], reverse=True)
    # create a list of the last X posts
    recentposts = []
    for post in sorted_posts:
        recentposts.append(post)
        if len(recentposts) == top:
            break
    stdlog('recent posts generated')
    return recentposts

def recentpage():
    '''create a markdown table for the last 100 posts based on the discovered value'''
    fetching_count = 200
    stdlog('generating recent posts page')
    recentpage = 'docs/recentposts.md'
    # delete contents of file
    with open(recentpage, 'w', encoding='utf-8') as f:
        f.close()
    writeline(recentpage, '# 📰 recent posts')
    writeline(recentpage, '')
    writeline(recentpage, '_last `' + str(fetching_count) + '` posts_')
    writeline(recentpage, '')
    writeline(recentpage, '| date | title | group |')
    writeline(recentpage, '|---|---|---|')
    for post in recentposts(fetching_count):
        # show friendly date for discovered
        date = post['discovered'].split(' ')[0]
        # replace markdown tampering characters
        title = post['post_title'].replace('|', '-')
        group = post['group_name'].replace('|', '-')
        urlencodedtitle = urllib.parse.quote_plus(title)
        grouplink = '[' + group + '](https://ransomwatch.telemetry.ltd/#/profiles?id=' + group + ')'
        line = '| ' + date + ' | [`' + title + '`](https://google.com/search?q=' + urlencodedtitle + ') | ' + grouplink + ' |'
        writeline(recentpage, line)
    stdlog('recent posts page generated')

def profilepage():
    '''
    create a profile page for each group in their unique markdown files within docs/profiles
    '''
    stdlog('generating profile pages')
    profilepage = 'docs/profiles.md'
    # delete contents of file
    with open(profilepage, 'w', encoding='utf-8') as f:
        f.close()
    writeline(profilepage, '# 🐦 profiles')
    writeline(profilepage, '')
    groups = openjson('groups.json')
    for group in groups:
        writeline(profilepage, '## ' + group['name'])
        writeline(profilepage, '')
        if group['captcha'] is True:
            writeline(profilepage, ':warning: _has a captcha_')
            writeline(profilepage, '')
        if group['parser'] is True:
            writeline(profilepage, '_parsing : `enabled`_')
            writeline(profilepage, '')
        else:
            writeline(profilepage, '_parsing : `disabled`_')
            writeline(profilepage, '')
        # add notes if present
        if group['meta'] is not None:
            writeline(profilepage, '_`' + group['meta'] + '`_')
            writeline(profilepage, '')
        if group['javascript_render'] is True:
            writeline(profilepage, '> fetching this site requires a headless browser')
            writeline(profilepage, '')
        if group['profile'] is not None:
            for profile in group['profile']:
                writeline(profilepage, '- ' + profile)
                writeline(profilepage, '')
        writeline(profilepage, '| title | available | version | last visit | fqdn')
        writeline(profilepage, '|---|---|---|---|---|')        
        for host in group['locations']:
            # convert date to ddmmyyyy hh:mm
            date = host['lastscrape'].split(' ')[0]
            date = date.split('-')
            date = date[2] + '/' + date[1] + '/' + date[0]
            time = host['lastscrape'].split(' ')[1]
            time = time.split(':')
            time = time[0] + ':' + time[1]
            if host['title'] is not None:
                line = '| ' + host['title'].replace('|', '-') + ' | ' + str(host['available']) +  ' | ' + str(host['version']) + ' | ' + time + ' ' + date + ' | `' + host['fqdn'] + '` |'
                writeline(profilepage, line)
            else:
                line = '| none | ' + str(host['available']) +  ' | ' + str(host['version']) + ' | ' + time + ' ' + date + ' | `' + host['fqdn'] + '` |'
                writeline(profilepage, line)
        writeline(profilepage, '')
        writeline(profilepage, '| post | date |')
        writeline(profilepage, '|---|---|')
        posts = openjson('posts.json')
        posts_sorted = sorted(posts, key=lambda x: x['discovered'], reverse=True)
        for post in posts_sorted:
            if post['group_name'] == group['name']:
                date = post['discovered'].split(' ')[0]
                date = date.split('-')
                date = date[2] + '/' + date[1] + '/' + date[0]
                line = '| ' + '`' + post['post_title'].replace('|', '') + '`' + ' | ' + date + ' |'
                writeline(profilepage, line)
        writeline(profilepage, '')
        stdlog('profile page for ' + group['name'] + ' generated')
    stdlog('profile page generation complete')

def rssfeed():
    '''
    create a RSS Feed with the last 50 entries 
    '''
    stdlog('generating RSS Fees')
    data = openjson('posts.json')
    data.sort(key=lambda item: datetime.strptime(item['discovered'], '%Y-%m-%d %H:%M:%S.%f'))

    rss = Element('rss', {'version': '2.0', 'xmlns:atom': 'http://www.w3.org/2005/Atom'})
    channel = SubElement(rss, 'channel')
    title = SubElement(channel, 'title')
    title.text = 'Ransomwatch RSS Feed'
    link = SubElement(channel, 'link')
    link.text = 'https://ransomwatch.telemetry.ltd/rss.xml'
    description = SubElement(channel, 'description')
    description.text = 'Last 50 entries monitoring by ransomwatch'

    # Add atom:link element
    atom_link = SubElement(channel, 'atom:link', href='https://ransomwatch.telemetry.ltd/rss.xml', rel='self', type='application/rss+xml')

    # Parcourez les données du fichier JSON et ajoutez un élément item pour chaque enregistrement
    for i in reversed(range(len(data)-50, len(data))):
      item = data[i]
      rss_item = SubElement(channel, 'item')
      item_title = SubElement(rss_item, 'title')
      item_title.text = "🏴‍☠️ " + str(item['group_name']) + " has just published a new victim : " + str(item['post_title']).replace('&amp;','&')
      item_link = SubElement(rss_item, 'link')
      item_link.text = 'https://ransomwatch.telemetry.ltd/#/profiles?id={}'.format(item['group_name'])
  
      item_guid = SubElement(rss_item, 'guid')
      item_guid.text = 'https://ransomwatch.telemetry.ltd/#/profiles?id=' + str(item['group_name'])  + '?' +md5GUID(item_title.text)
  
      date_iso = item['published']
      date_rfc822 = datetime.strptime(date_iso, '%Y-%m-%d %H:%M:%S.%f').strftime('%a, %d %b %Y %H:%M:%S +0000')
  
      item_pubdate = SubElement(rss_item, 'pubDate')
      item_pubdate.text = date_rfc822

    rss_str = tostring(rss, encoding='unicode')
    with open('./docs/rss.xml', 'w') as f:
      f.write(rss_str)
    stdlog('RSS Feed page generation complete')

def main():
    stdlog('generating doco')
    mainpage()
    indexpage()
    recentpage()
    statspage()
    profilepage()
    rssfeed()
    # if posts.json has been modified within the last 10 mins, assume new posts discovered and recreate graphs
    if os.path.getmtime('posts.json') > (time.time() - 600):
        stdlog('posts.json has been modified within the last 45 mins, assuming new posts discovered and recreating graphs')
        trend_posts_per_day()
        plot_posts_by_group()
        pie_posts_by_group()
        plot_posts_by_group_past_7_days()
    else:
        stdlog('posts.json has not been modified within the last 45 mins, assuming no new posts discovered')
