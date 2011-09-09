#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from django.utils.html import escape

class NumericRow(db.Model):
   table = db.StringProperty()
   row = db.IntegerProperty()
   index = db.FloatProperty()
   vals = db.ListProperty(float)


class Title(db.Model):
   table = db.StringProperty()
   col = db.IntegerProperty()
   title = db.StringProperty()

class TableDescription(db.Model):
   name = db.StringProperty()
   description = db.TextProperty()

class ShowTablesHandler(webapp.RequestHandler):
    def get(self):
	html = """<html>
<head><title>Web Tobin Server, upload csv</title></head>
<body>
<h1>Available tables</h1>
<ul>
"""
	tables = TableDescription.all().fetch(100)
	for table in tables:
		html += "<li>"
		html += escape(table.name)
		html += "<br>"
		html += escape(table.description)
		html += "</li>"
	html += "</ul></body></html>"
        self.response.out.write(html)

class MainHandler(webapp.RequestHandler):
    def get(self):
	html = """<html>
<head><title>Web Tobin Server, upload csv</title></head>
<body>
<h1> Upload CSV</h1>
<form id="upload_form" action="/upload" enctype="multipart/form-data" method="post">
  CSV File: <input type="file" name="file" id="file" /> <br>
  Table Name: <input type="text" name="tableName" /> <br>
  Description:<br> <textarea cols="80" rows="30" name="description" ></textarea> <br>
  <input type="submit" value="Upload" />
</form>
</body>
</html>"""
        self.response.out.write(html)

import urllib2

class DeleteHandler(webapp.RequestHandler):
    def get(self, tableName):
	tableName = urllib2.unquote(tableName).decode('utf-8')
	db.delete(NumericRow.all().filter('table = ', tableName))
	db.delete(Title.all().filter('table = ', tableName))
	db.delete(TableDescription.all().filter('name = ', tableName))
	self.response.out.write("Table [" + tableName +"] deleted.")

from operator import attrgetter

class TableHandler(webapp.RequestHandler):
    def getParams(self, name):
	if not self.request.get(name):
		return None
        params = self.request.get(name).split(',')
	return map(lambda x: urllib2.unquote(x), params)
    def get(self, tableName):
	callback = self.request.get('callback').encode('utf-8')
        fields = self.getParams('f')
	range = self.getParams('r')
	if range:
		rangeBeg = float(range[0])
		rangeEnd = float(range[1])
	num = self.request.get('n')
	if num:
		num = int(num)
	else:
		num = 10 #default, very small.
        body = []
        body.append('{"titles": [')
	
	tableName = urllib2.unquote(tableName).decode('utf-8')

	titles = Title.all().filter('table = ', tableName).order('col').fetch(1000)
	if fields:
		titles = filter(lambda x: x.title in fields, titles)
        titleLen = len(titles)

	self.appendTitles(body, titles)
        body.append(',')
	# temp implementation, all must be numeric
	self.appendTypes(body, titles)
        body.append(',')
	if range:
		rows = self.getRowsWithRange(tableName, rangeBeg, rangeEnd, num)
	else:
		rows = self.getRows(tableName, num)
	rows = self.onlyTitlesRow(titles, rows)
	self.appendData(body, rows)
        body.append("}")
        body = "".join(body)
	if callback:
		body = ('%s(%s);' % (callback, body))
	self.response.headers['Content-Type']='text/javascript'
	self.response.headers['Content-Length'] = len(body)
	self.response.out.write(body)
    def onlyTitlesRow(self, titles, rows):
	colNums = [t.col for t in titles]
	ret = []
	for oneRow in rows:
		oneRowRet = []
		if 0 in colNums:
			oneRowRet.append(oneRow.index)
		for i, val in enumerate(oneRow.vals):
			if (i+1) in colNums:
				oneRowRet.append(val)
		ret.append(oneRowRet)
	return ret
    def appendTitles(self, body, titles):
        first = True
        for title in titles:
           if first:
               first = False
           else:
              body.append(",")
           body.append('"')
           body.append(title.title.encode('utf-8'))
           body.append('"')
        body.append(']')
    def appendTypes(self, body, titles):
	body.append('"types": [')
        first = True
        for t in titles:
           if first:
               first = False
           else:
              body.append(',')
           body.append('"numeric"')
        body.append(']')
    def appendData(self, body, rows):
        body.append('"data": [' )
        first1 = True
	for row in rows:
		if first1:
			first1 = False
		else :
			body.append(",")
		body.append("[")
		first = True
		for col in row:
			if first:
				first = False
			else:
				body.append(",")
			body.append(str(col))
		body.append("]")
	body.append("]")
    def getRows(self, tableName, num):
	return NumericRow.all().filter('table = ', tableName).order('-row').fetch(num)
    def getRowsWithRange(self, tableName, rangeBeg, rangeEnd, num):
	rows = NumericRow.all().filter('table = ', tableName).filter('index >=', rangeBeg).filter('index <=', rangeEnd).fetch(num)
	rows.sort(key=attrgetter('row'), reverse=True)
	return rows



import csv
import StringIO

class UploadHandler(webapp.RequestHandler): 
   def post(self): 
     fileData = self.request.get("file")
     tableName = self.request.get("tableName")
     if not fileData or not tableName:
         return self.redirect('/')
     description = self.request.get("description")
     
     putCand = []
     table = TableDescription(name=tableName, description=description)
     putCand.append(table)
     
     stringReader = csv.reader(StringIO.StringIO(fileData))
     titles = stringReader.next()
     for i, title in enumerate(titles):
        t = Title(table=tableName, col=i, title=title.decode('utf-8'))
        putCand.append(t)
     for irow, row in enumerate(stringReader): 
	frow = []
	for col in row:
		frow.append(float(col))
	rowModel = NumericRow(table=tableName, index = frow[0], row=irow, vals=frow[1:])
	putCand.append(rowModel)
        # avoid too much contention 
        # 5000 was too much.
        if len(putCand) > 1000:
           db.put(putCand)
           putCand = []
     db.put(putCand)
     self.response.out.write("Table [" + tableName +"] uploaded.")


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
					  ('/upload', UploadHandler),
					  ('/delete/([^/]*)/', DeleteHandler),
					  ('/tables', ShowTablesHandler),
					   ('/t/([^/]*)/json', TableHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
