'''
References

Beautiful Soup Documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
MySQL Python Connector: https://pymysql.readthedocs.io/en/latest/
Requests Module Documentation: https://pypi.org/project/requests/2.7.0/
'''
import requests
import urllib.parse
import re as regularExpression
import json
from bs4 import BeautifulSoup
import pymysql.cursors
import os


'''
12.07.2019

Functions to create:

isScrapeComplete()
logError()
insert()
'''

'''
GET THE TOTAL NUMBER OF ARCHIVE PAGES
'''
response = requests.get('https://www.wired.com/most-recent/page/1')
soup = BeautifulSoup(response.text, 'html.parser')
soup_results = soup.find(class_ = 'pagination-component__pages')
archivePageOptions = []

for item in soup_results.contents:
    try:
        archivePageOptions.append(int(item.a.contents[0]))
    except Exception as e:
        print(e)

countTotalPages = max(archivePageOptions)


'''
GET THE NUMBER OF LINKS PER ARCHIVE PAGE
'''

searchExpression = 'window.__INITIAL_STATE__ = JSON.parse\(decodeURIComponent\("(.*)"\)\)'
match = regularExpression.search(searchExpression,response.text)
jsonString = urllib.parse.unquote(match.group(1))

deserializedObject = json.loads(jsonString)
newsArticles = deserializedObject['primary']['items']
countRecordsPerPage = len(newsArticles)


'''
SCRAPE EACH PAGE OF THE WEBSITE AND STORE RESULTS IN DATABASE
'''

# get initial count of database records
connection = pymysql.connect(
    host='localhost'
    , user= os.environ['databaseUser']
    , password= os.environ['databasePassword']
    , database='NewsAggregator'
    , cursorclass=pymysql.cursors.DictCursor)

cursor = connection.cursor()
cursor.execute("SELECT COUNT(*) AS count FROM NewsArticle")

results = cursor.fetchone()
while (results != None):
    countDatabaseRecords = results['count']
    results = cursor.fetchone()

currentPage = 1
while (countDatabaseRecords <= (countTotalPages - 1) * countRecordsPerPage):
    print(countDatabaseRecords)
    print(currentPage)
    try:
        response = requests.get(f'https://www.wired.com/most-recent/page/{currentPage}')
        searchExpression = 'window.__INITIAL_STATE__ = JSON.parse\(decodeURIComponent\("(.*)"\)\)'
        match = regularExpression.search(searchExpression,response.text)
        jsonString = urllib.parse.unquote(match.group(1))

        deserializedObject = json.loads(jsonString)
        newsArticles = deserializedObject['primary']['items']

    except Exception as e:
        e = str(e).replace('\'','')
        cursor.execute(f"INSERT INTO NewsArticle_ScrapeErrorLog (message, page_) VALUES ('{e}', {currentPage})")
        connection.commit()

    for article in newsArticles:
        articlePubDate = article['pubDate']
        articleURL = 'https://www.wired.com/' + article['url']
        articleTitle = article['hed'].replace('\'','')
        articleContributor = str(article['contributors']).replace('\'','')

        try:
            cursor.execute(f"INSERT INTO NewsArticleContributor (url, contributor) VALUES ('{articleURL}', '{articleContributor}')")
            connection.commit()
        except Exception as e:
            e = str(e).replace('\'','')
            cursor.execute(f"INSERT INTO NewsArticleContributor_ScrapeErrorLog (message, page_) VALUES ('{e}', {currentPage})")
            connection.commit()

        try:
            countAffectedRows = cursor.execute(f"INSERT INTO NewsArticle (title, url, publishDate) VALUES ('{articleTitle}','{articleURL}','{articlePubDate}')")
            connection.commit()
        except Exception as e:
            e = str(e).replace('\'','')
            cursor.execute(f"INSERT INTO NewsArticle_ScrapeErrorLog (message, page_) VALUES ('{e}', {currentPage})")
            connection.commit()
            countAffectedRows = 0

        connection.commit()
        countDatabaseRecords += countAffectedRows
    currentPage += 1

connection.commit()
connection.close()


raw_input('Press enter key to terminate program')
