#!/usr/bin/env python

import sys
import time
import MySQLdb
import dbconfig

class DBUpgradeTools(object):
	#============================
	#== PRIVATE FUNCTIONS
	#============================
	def __init__(self, confname, dbname=None, drop=False):
		self.drop = drop
		self.confname = confname
		### get database config from sinedon.cfg
		dbconf = dbconfig.getConfig(self.confname)
		### if database name is not config name, e.g., ap212 and appiondata
		if dbname is not None and dbname != dbconf['db']:
			self.dbname = dbname
			dbconf = dbconfig.setConfig(self.confname, db=dbname)
		else:
			self.dbname = dbconf['db']
		print "\033[32mconnected to db '%s' on server '%s'\033[0m"%(dbconf['db'], dbconf['host'])
		### connect to db
		db = MySQLdb.connect(**dbconf)
		### create cursor
		self.cursor = db.cursor()
		self.debug = 15
		self.defid = 'int(20) NOT NULL auto_increment'
		self.link = 'int(20) NULL DEFAULT NULL'
		self.int = 'int(20) NULL DEFAULT NULL' 
		self.bool = 'tinyint(1) NULL DEFAULT 0' 
		self.str = 'text NULL DEFAULT NULL' 
		self.float = 'double NULL DEFAULT NULL'
		self.timestamp = 'timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP' 

	#==============
	def databaseExists(self, dbname):
		query = "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '%s';"%(dbname)
		if self.debug > 3:
			print query
		self.cursor.execute(query)
		numrows = int(self.cursor.rowcount)
		if numrows > 0:
			return True
		return False

	#==============
	def getDatabaseName(self):
		return self.dbname

	#==============
	def getSinedonName(self):
		return self.confname

	#==============
	def validTableName(self, table):
		"""
		check name of table for security reasons
		"""
		if "." in table:
			print "\033[31merror . in table name\033[0m"
			sys.exit(1)
			return False
		if ";" in table:
			print "\033[31merror ; in table name\033[0m"
			sys.exit(1)
			return False
		if "`" in table:
			print "\033[31merror ` in column name\033[0m"
			sys.exit(1)
			return False
		return True

	#==============
	def tableExists(self, table):
		"""
		check if table exists
		"""
		query = "SHOW TABLES LIKE '%s';"%(table)
		if self.debug > 2:
			print query
		self.cursor.execute(query)
		numrows = int(self.cursor.rowcount)
		if numrows > 0:
			return True
		return False

	#==============
	def validColumnName(self, column, allowspace=False):
		"""
		check name of column for security reasons
		"""
		if "." in column:
			print "\033[31merror . in column name\033[0m"
			sys.exit(1)
			return False
		if ";" in column:
			print "\033[31merror ; in column name\033[0m"
			sys.exit(1)
			return False
		if "`" in column:
			print "\033[31merror ` in column name\033[0m"
			sys.exit(1)
			return False
		if not allowspace and " " in column:
			print "\033[31merror ' ' in column name\033[0m"
			sys.exit(1)
			return False
		return True

	#==============
	def columnExists(self, table, column):
		"""
		check if column exists
		"""
		if self.tableExists(table) is False:
			if self.debug > 0:
				print "\033[33mcannot check column, table %s does not exist\033[0m"%(table)
			return False
		query = "SHOW COLUMNS FROM `%s` WHERE Field='%s';"%(table, column)
		if self.debug > 2:
			print query
		self.cursor.execute(query)
		numrows = int(self.cursor.rowcount)
		if numrows > 0:
			return True
		return False

	#==============
	def columnIndexExists(self, table, column):
		"""
		check if column exists
		"""
		if self.tableExists(table) is False:
			if self.debug > 0:
				print "\033[33mcannot check column, table %s does not exist\033[0m"%(table)
			return False
		query = "SHOW INDEX FROM  `%s` WHERE Column_name='%s';"%(table, column)
		if self.debug > 2:
			print query
		self.cursor.execute(query)
		numrows = int(self.cursor.rowcount)
		if numrows > 0:
			return True
		return False

	#==============
	def getColumnDefinition(self, table, column):
		"""
		get column definition (e.g., TINYINT(1) NULL DEFAULT 0)
		"""
		#query = "SHOW CREATE TABLE `%s`;"%(table)
		#self.cursor.execute(query)
		#print self.cursor.fetchone()

		query = "DESCRIBE `%s` `%s`;"%(table, column)
		if self.debug > 2:
			print query
		self.cursor.execute(query)
		result = self.cursor.fetchone()
		if not result:
			print "\033[31mcolumn definition not found %s.%s\033[0m"%(table, column)
			sys.exit(1)
			return None
		coldef = "%s "%(result[1])
		if result[2] == "NO":
			coldef += "NOT NULL "
		else:
			coldef += "NULL "
		if result[4]:
			coldef += "default %s "%(result[4])
		if result[5]:
			coldef += result[5]+" "
		return coldef

	#============================
	#== PUBLIC FUNCTIONS
	#============================

	#==============
	def executeCustomSQL(self, query):
		"""
		execute custom query
		"""
		if self.debug > 0:
			print "CUSTOM: \033[33m", query, "\033[0m"
		t0 = time.time()
		self.cursor.execute(query)
		if self.debug > 0 and time.time()-t0 > 20:
			print "custom query time: %.1f min"%((time.time()-t0)/60.0)
		return True

	#==============
	def returnCustomSQL(self, query):
		"""
		execute custom query
		"""
		if self.debug > 0:
			print "CUSTOM: \033[33m", query, "\033[0m"
		t0 = time.time()
		self.cursor.execute(query)
		if self.debug > 0 and time.time()-t0 > 20:
			print "custom query time: %.1f min"%((time.time()-t0)/60.0)
		return self.cursor.fetchall()

	#==============
	def renameTable(self, table1, table2):
		"""
		rename table1 to table2
		"""
		if self.validTableName(table1) is False:
			return False
		if self.validTableName(table2) is False:
			return False
		if self.tableExists(table1) is False:
			if self.debug > 0:
				print "\033[33mcannot rename %s to %s, table does not exist\033[0m"%(table1, table2)
			return
		if self.tableExists(table2) is True:
			print "\033[31mcannot rename %s to %s, table exists\033[0m"%(table1, table2)
			sys.exit(1)
			return

		query = "RENAME TABLE `%s` TO `%s`;"%(table1, table2)
		if self.debug > 1:
			print query
		self.cursor.execute(query)

		if self.tableExists(table2) is False:
			print "\033[31mfailed to rename %s to %s\033[0m"%(table1, table2)
			sys.exit(1)
			return

		if self.debug > 0:
			print "\033[32mrenamed table %s to %s\033[0m"%(table1, table2)
		return True

	#==============
	def renameColumn(self, table, column1, column2, columndefine=None):
		"""
		rename column1 to column2 in table
		"""
		if self.validTableName(table) is False:
			return False
		if self.validColumnName(column1, allowspace=True) is False:
			return False
		if self.validColumnName(column2) is False:
			return False

		if self.columnExists(table, column1) is False:
			if self.debug > 0:
				print "\033[33mcannot rename %s to %s, column does not exist\033[0m"%(column1, column2)
			return False
		if self.columnExists(table, column2) is True:
			print "\033[31mcannot rename %s to %s, column exists\033[0m"%(column1, column2)
			sys.exit(1)
			return False

		if columndefine is None:
			columndefine = self.getColumnDefinition(table, column1)
		if not columndefine:
			return False
		query = "ALTER TABLE `%s` CHANGE `%s` `%s` %s;"%(table, column1, column2, columndefine)
		if self.debug > 1:
			print query

		t0 = time.time()
		self.cursor.execute(query)
		if self.debug > 0 and time.time()-t0 > 20:
			print "column rename time: %.1f min"%((time.time()-t0)/60.0)

		if self.columnExists(table, column2) is False:
			print "\033[31mfailed to rename %s to %s\033[0m"%(column1, column2)
			sys.exit(1)
			return False

		if self.debug > 0:
			print "\033[32mrenamed column %s to %s\033[0m"%(column1, column2)



		return True

	#==============
	def addColumn(self, table, column, column_definition, index=False):
		"""
		add a column to a table
		"""
		if self.validTableName(table) is False:
			return False
		if self.validColumnName(column) is False:
			return False
		if self.tableExists(table) is False:
			if self.debug > 0:
				print "\033[33mcannot add column %s, table does not exist\033[0m"%(column)
			return False
		if self.columnExists(table, column) is True:
			if self.debug > 0:
				print "\033[33mcannot add column %s, column exists\033[0m"%(column)
			return False

		query = "ALTER TABLE `%s` ADD COLUMN `%s` %s;"%(table, column, column_definition)
		if self.debug > 1:
			print query
		self.cursor.execute(query)

		if self.columnExists(table, column) is False:
			print "\033[31mfailed to add column %s\033[0m"%(column)
			sys.exit(1)
			return False

		if index is True:
			self.indexColumn(table, column)

		if self.debug > 0:
			print "\033[32madded column %s\033[0m"%(column)
		return True

	#==============
	def createTable(self, table):
		"""
		create table with DEF_id and DEF_timestamp
		"""
		if self.validTableName(table) is False:
			return False
		if self.tableExists(table) is True:
			print "\033[31mcannot create table %s, table exists\033[0m"%(table)
			sys.exit(1)
			return False

		query = "CREATE TABLE `%s` \n"%(table)
		query += "( \n"
		### add DEF_id and DEF_timestamp
		query += "`DEF_id` int(20) NOT NULL auto_increment, \n"
		query += "`DEF_timestamp` "+self.timestamp+", \n"
		### set keys
		query += "PRIMARY KEY (`DEF_id`), \n"
		query += "KEY `DEF_timestamp` (`DEF_timestamp`) \n"
		### set defaults
		query += ") ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;\n"
		if self.debug > 1:
			print query
		self.cursor.execute(query)

		if self.tableExists(table) is False:
			print "\033[31mfailed to create table %s\033[0m"%(table)
			sys.exit(1)
			return False

		if self.debug > 0:
			print "\033[32mcreated table %s\033[0m"%(table)
		return True

	#==============
	def dropColumn(self, table, column):
		"""
		drop a column from a table
		"""
		if self.drop is False:
			print "\033[31mcannot drop column, safe mode enabled\033[0m"
			sys.exit(1)
			return False
		if self.validTableName(table) is False:
			return False
		if self.validColumnName(column, allowspace=True) is False:
			return False
		if self.columnExists(table, column) is False:
			if self.debug > 0:
				print "\033[33mcannot drop column %s, column does not exist\033[0m"%(column)
			return False

		query = "ALTER TABLE `%s` DROP COLUMN `%s` ;"%(table, column)
		if self.debug > 1:
			print query
		self.cursor.execute(query)

		if self.columnExists(table, column) is True:
			print "\033[31mfailed to drop column %s\033[0m"%(column)
			sys.exit(1)
			return False

		if self.debug > 0:
			print "\033[32mdropped column %s\033[0m"%(column)
		return True

	#==============
	def indexColumn(self, table, column, length=None):
		"""
		add index to a column in a table
		"""
		if self.validTableName(table) is False:
			return False
		if self.validColumnName(column) is False:
			return False
		if self.columnExists(table, column) is False:
			if self.debug > 0:
				print "\033[33mcannot index column %s, column does not exist\033[0m"%(column)
			return False
		if self.columnIndexExists(table, column) is True:
			if self.debug > 0:
				print "\033[33mcannot index column %s, column is already indexed\033[0m"%(column)
			return False

		if length is None:
			query = "ALTER TABLE `%s` ADD INDEX (`%s`) ;"%(table, column)
		else:
			query = "CREATE INDEX %s_index%d ON %s (%s(%d)); ;"%(column, length, table, column, length)
		if self.debug > 1:
			print query
		self.cursor.execute(query)

		if self.debug > 0:
			print "\033[32mindex column %s\033[0m"%(column)
		return True

	#==============
	def changeColumnDefinition(self, table, column, definition):
		"""
		set new column definition (e.g., TINYINT(1) NULL DEFAULT 0)
		"""
		if self.validTableName(table) is False:
			return False
		if self.validColumnName(column, allowspace=True) is False:
			return False
		if self.columnExists(table, column) is False:
			if self.debug > 0:
				print "\033[33mcannot modify column %s, column does not exist\033[0m"%(column)
			return False

		query = "ALTER TABLE `%s` MODIFY `%s` %s;"%(table, column, definition)
		if self.debug > 2:
			print query
		self.cursor.execute(query)

		if self.debug > 0:
			print "\033[32mchanged column %s definition\033[0m"%(column)
		return True

	#==============
	def getAllTables(self):
		"""
		get all tables in database
		"""
		query = "SHOW TABLES;"
		if self.debug > 1:
			print query
		self.cursor.execute(query)
		tabledatas = self.cursor.fetchall()
		tablelist = []
		for tabledata in tabledatas:
			tablelist.append(tabledata[0])
		if self.debug > 0:
			print "\033[32mfound %d tables\033[0m"%(len(tablelist))
		return tablelist

	#============================
	#== END CLASS
	#============================

if __name__ == "__main__":
	#basic test
	a = DBUpgradeTools('ap212', 'appiondata')
	print a.getColumnDefinition('ApPathData', 'DEF_id')
	print a.getColumnDefinition('ApPathData', 'path')






