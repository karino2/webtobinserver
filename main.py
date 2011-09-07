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

class NumericCell(db.Model):
   table = db.StringProperty()
   row = db.IntegerProperty()
   col = db.IntegerProperty()
   val = db.FloatProperty()


class Title(db.Model):
   table = db.StringProperty()
   col = db.IntegerProperty()
   title = db.StringProperty()

class TableDescription(db.Model):
   name = db.StringProperty()
   description = db.TextProperty()


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

class TableHandler(webapp.RequestHandler):
    def getParams(self, name):
	if not self.request.get(name):
		return None
        params = self.request.get(name).split(',')
	return map(lambda x: urllib2.unquote(x), params)
    def get(self, tableName):
	callback = self.request.get('callback')
        fields = self.getParams('f')
	range = self.getParams('r')
	if range:
		rangeField = range[0]
		rangeBeg = float(range[1])
		rangeEnd = float(range[2])
	num = self.request.get('n')
	if num:
		num = int(num)
	else:
		num = 10 #default, very small.
        body = []
        body.append('{"titles": [')
	
	#print OK
	#tableName = urllib2.unquote(tableName)
	
        #print OK, set OK but no hit
        #tableName = urllib2.unquote(tableName)
        #tableName = tableName.decode('utf-8')

	#self.response.out.write('table=' + str(type(tableName)))
        #return
        
        #tableName = tableName.encode('utf-8')
        #tableName = tableName.decode('utf-8')
	#self.response.out.write('table=' + unicode(tableName, 'utf-8'))
        #tableName = unicode(tableName, 'utf-8')
	#self.response.out.write('table=' + tableName)
	#return 

	tableName = urllib2.unquote(tableName)

	titles = Title.all().filter('table = ', tableName).order('col').fetch(1000)
	titles = filter(lambda x: x.title in fields, titles)
        titleLen = len(titles)

	self.appendTitles(body, titles)
        body.append(',')
	# temp implementation, all must be numeric
	self.appendTypes(body, titles)
        body.append(',')
        # TODO: num
	if range:
		cols = self.getCellsWithRange(titles, tableName, rangeField, rangeBeg, rangeEnd, num)
	else:
		cols = self.getCells(titles, tableName, num)
	self.appendData(body, cols)
        body.append("}")
        body = "".join(body)
	if callback:
		body = ('%s(%s);' % (callback, body))
	self.response.headers['Content-Type']='text/javascript'
	self.response.headers['Content-Length'] = len(body)
	self.response.out.write(body)
    def appendTitles(self, body, titles):
        first = True
        for title in titles:
           if first:
               first = False
           else:
              body.append(",")
           body.append('"')
           body.append(title.title)
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
    def appendData(self, body, cols):
        body.append('"data": [' )
        cur = 0
	oneCol = cols[0]
        first1 = True
	for irow in range(0, len(oneCol)):
		if first1:
			first1 = False
		else :
			body.append(",")
		body.append("[")
	        first = True
		for col in cols:
			if first:
				first = False
			else:
				body.append(",")
			body.append(str(col[irow].val))
		body.append("]")
        body.append("]")
    def getCells(self, titles, tableName, num):
	cols = []
	for t in titles:
		baseQuery = NumericCell.all().filter('table = ', tableName).order('-row')
		oneCol = baseQuery.filter('col =', t.col).fetch(num)
		cols.append(oneCol)
	return cols
    def getCellsWithRange(self, titles, tableName, rangeField, rangeBeg, rangeEnd, num):
	cols = []
	targetCol = [t.col for t in titles if t.title == rangeField][0]
	target = NumericCell.all().filter('table = ', tableName).filter('col = ', targetCol).filter('val >=', rangeBeg).filter('val <=', rangeEnd).fetch(num)
	target.sort(lambda x, y: cmp(y.val, x.val))
	rowRangeEnd = target[0].row
	rowRangeBeg = target[-1].row
	for t in titles:
		if t.col == targetCol:
			cols.append(target)
			continue
		query = NumericCell.all().filter('table = ', tableName)
		query = query.filter('row >=', rowRangeBeg).filter('row <=', rowRangeEnd)
		oneCol = query.order('-row').filter('col =', t.col).fetch(num)
		cols.append(oneCol)
	return cols



import csv
import StringIO

class UploadHandler(webapp.RequestHandler): 
   def post(self): 
     fileData = self.request.get("file")
     tableName = self.request.get("tableName").encode('utf-8')
     # print OK, that is, not Unicode... self.response.out.write("tableName " + tableName)
     if not fileData or not tableName:
         return self.redirect('/')
     description = self.request.get("description")
     
     putCand = []
     table = TableDescription(name=tableName, description=description)
     putCand.append(table)
     
     stringReader = csv.reader(StringIO.StringIO(fileData))
     titles = stringReader.next()
     # self.response.out.write("title! " + str(len(titles))  +"\n")
     for i, title in enumerate(titles):
        #self.response.out.write(title + ",") 
        t = Title(table=tableName, col=i, title=title)
        putCand.append(t)
     # self.response.out.write("\n")
     stringReader.next()
     for nrow, row in enumerate(stringReader): 
	for ncol, col in enumerate(row):
           cell = NumericCell(table=tableName, row=nrow, col=ncol, val=float(col))
           putCand.append(cell)
     db.put(putCand)


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
					  ('/upload', UploadHandler),
					   ('/t/([^/]*)/json', TableHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
