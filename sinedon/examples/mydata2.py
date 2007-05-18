'''
This example defines the structure of another database that will reference
the database defined in mydata1.py.

Instances of OtherData will have a refernce to SomeData (defined locally in
the same database) and also a reference to TData (defined in a different
database)
'''

import sinedon
import mydata1 

class SomeData(sinedon.Data):
	typemap = sinedon.Data.typemap + (
		('name', str),
		('description', str),
	)

class OtherData(sinedon.Data):
	typemap = sinedon.Data.typemap + (
		('name', str),
		('t', mydata1.TData),
		('abc', SomeData),
	)
