'''
References

Beautiful Soup Documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
MySQL Python Connector: https://pymysql.readthedocs.io/en/latest/
Requests Module Documentation: https://pypi.org/project/requests/2.7.0/
'''

'''
def isComplete(self):
  check to see if current page is the final page
  OR
  if the current page has been incremented NUMBER times since last check
    check whether the most recent cached news articles have already been scraped


while !self.isComplete():
  request web data
  parse web data for news articles
  insert news article contributors into database
  insert news articles into database
  increment current news article database record count

def __init__(self):
  initialize total number of archive pages
  initialize current database record count


def insertIntoDatabase_NewsArticles():
  if page has been incremented NUMBER times since last check
    check whether the most recent cached articles have already been scraped
    if so - raise error and end program
  increment total database record count
  insert articles into database

def insertIntoDatabase_NewsArticleContributors():
  if page has been incremented NUMBER times since last check
    check whether duplicates are being inserted
    if so - raise error and end program
  insert article contributors into database
'''

import requests
import urllib.parse
import re
import json
from bs4 import BeautifulSoup
import pymysql.cursors
import os



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



class WiredNewsScraper(object):

    def __init__(self, connection):
        self.connection = connection
        self.page_current = 1
        self.page_lastValidation = 1

    def getNewsArticles(self, currentPage):
            result = []
            try:
                webResponse = requests.get(f'https://www.wired.com/most-recent/page/{currentPage}')
                searchExpression = 'window.__INITIAL_STATE__ = JSON.parse\(decodeURIComponent\("(.*)"\)\)'
                searchMatch = re.search(searchExpression,webResponse.text)
                articlesSerializedJSON = urllib.parse.unquote(searchMatch.group(1))

                articlesDeserializedJSON = json.loads(articlesSerializedJSON)
                articles = articlesDeserializedJSON['primary']['items']

            except Exception as e:
                e = str(e).replace('\'','')
                cursor.execute(f"INSERT INTO NewsArticle_ScrapeErrorLog (message, page_) VALUES ('{e}', {currentPage})")
                connection.commit()

            for article in articles:
                articlePubDate = article['pubDate']
                articleURL = 'https://www.wired.com/' + article['url']
                articleTitle = article['hed'].replace('\'','')
                articleContributor = str(article['contributors']).replace('\'','')
                result.append({'pubDate':articlePubDate, 'url':articleURL, 'title':articleTitle, 'contributor':articleContributor})

            return result


    def insertIntoDatabase_NewsArticle(self, articleURL, articleTitle, articlePubDate):
        try:
            countAffectedRows = cursor.execute(f"INSERT INTO NewsArticle (title, url, publishDate) VALUES ('{articleTitle}','{articleURL}','{articlePubDate}')")
            connection.commit()
        except Exception as e:
            e = str(e).replace('\'','')
            cursor.execute(f"INSERT INTO NewsArticle_ScrapeErrorLog (message, page_) VALUES ('{e}', {self.currentPage})")
            connection.commit()
            countAffectedRows = 0

        connection.commit()

    def insertIntoDatabase_NewsArticleContributor(self, articleURL, articleContributor):
    	try:
    		cursor.execute(f"INSERT INTO NewsArticleContributor (url, contributor) VALUES ('{articleURL}', '{articleContributor}')")
    		connection.commit()
    	except Exception as e:
    		e = str(e).replace('\'','')
    		cursor.execute(f"INSERT INTO NewsArticleContributor_ScrapeErrorLog (message, page_) VALUES ('{e}', {self.currentPage})")

        connection.commit()

    def isComplete(self):
        # if (self.page_current - self.page_lastValidation > 100):
        return True

    def scrape():
        while (not scraper.isComplete()):
            articles = scraper.getNewsArticles(self.page_current)
            for article in articles:
                insertIntoDatabase_NewsArticleContributor(article['url'], newsArticle['contributor'])
                insertIntoDatabase_NewsArticle(article['url'], article['title'], article['pubDate'])
            self.page_current += 1
        connection.close()


connection = pymysql.connect(
    host='localhost'
    , user= os.environ['databaseUser']
    , password= os.environ['databasePassword']
    , database='NewsAggregator'
    , cursorclass=pymysql.cursors.DictCursor)

scraper = WiredNewsScraper(connnection)
scraper.scrape()
