'''
References

Beautiful Soup Documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
MySQL Python Connector: https://pymysql.readthedocs.io/en/latest/
Requests Module Documentation: https://pypi.org/project/requests/2.7.0/
'''

import requests
import urllib.parse
import re
import json
from bs4 import BeautifulSoup
import pymysql.cursors
import os

class WiredNewsScraper(object):

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self.page_current = 1
        self.page_lastValidation = 1
        self.articles = None

    def getNewsArticles(self):
            result = []
            try:
                webResponse = requests.get(f'https://www.wired.com/most-recent/page/{self.page_current}')
                searchExpression = 'window.__INITIAL_STATE__ = JSON.parse\(decodeURIComponent\("(.*)"\)\)'
                searchMatch = re.search(searchExpression,webResponse.text)
                articlesSerializedJSON = urllib.parse.unquote(searchMatch.group(1))

                articlesDeserializedJSON = json.loads(articlesSerializedJSON)
                articles = articlesDeserializedJSON['primary']['items']

            except Exception as e:
                e = str(e).replace('\'','')
                self.cursor.execute(f"INSERT INTO NewsArticle_ScrapeErrorLog (message, page_) VALUES ('{e}', {self.page_current})")
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
            countAffectedRows = self.cursor.execute(f"INSERT INTO NewsArticle (title, url, publishDate) VALUES ('{articleTitle}','{articleURL}','{articlePubDate}')")
            self.connection.commit()
        except Exception as e:
            e = str(e).replace('\'','')
            self.cursor.execute(f"INSERT INTO NewsArticle_ScrapeErrorLog (message, page_) VALUES ('{e}', {self.page_current})")
            self.connection.commit()
            countAffectedRows = 0

    def insertIntoDatabase_NewsArticleContributor(self, articleURL, articleContributor):
        try:
            self.cursor.execute(f"INSERT INTO NewsArticleContributor (url, contributor) VALUES ('{articleURL}', '{articleContributor}')")
            self.connection.commit()
        except Exception as e:
            e = str(e).replace('\'','')
            self.cursor.execute(f"INSERT INTO NewsArticleContributor_ScrapeErrorLog (message, page_) VALUES ('{e}', {self.page_current})")
            self.connection.commit()

    def isArticleInDatabase(self, article):
        countRecords = self.cursor.execute(f"SELECT count(*) AS count from NewsArticleContributor where url = '{article['url']}'")
        if (countRecords > 0):
            return True
        else:
            return False


    def isComplete(self):
        if (self.page_current - self.page_lastValidation > 10):
            for article in self.articles:
                if not self.isArticleInDatabase(article):
                    return False
                    self.page_lastValidation = self.page_current
                else:
                    return True

    def scrape(self):
        while (not self.isComplete()):
            self.articles = self.getNewsArticles()
            for article in self.articles:
                self.insertIntoDatabase_NewsArticleContributor(article['url'], article['contributor'])
                self.insertIntoDatabase_NewsArticle(article['url'], article['title'], article['pubDate'])
            self.page_current += 1
            print(self.page_current)
            print(self.page_lastValidation)
        connection.close()


connection = pymysql.connect(
    host='localhost'
    , user= os.environ['databaseUser']
    , password= os.environ['databasePassword']
    , database='NewsAggregator'
    , cursorclass=pymysql.cursors.DictCursor)

scraper = WiredNewsScraper(connection)
scraper.scrape()
