import MySQLdb
import time
import BF_logging as lg

#mysql connection hostgator

db = MySQLdb.connect(host="192.185.4.111",
					 user="afy2003",
					  passwd="E4rmsrV+tw3r",
					  db="afy2003_BF")

cur = db.cursor()

def upadte_database(data):
	try:

		time = data[0]
		magnet_temp = data[1]
		sample_temp = data[2]
		level = data[3]
		field = data[4]

		cur.execute("""INSERT INTO Status
						VALUES ({},{},{},{},{},{},{})""".format(time, magnet_temp, sample_temp, level, field))
		db.commit()

	except:
		time.sleep(60)
		print "RECONNECTING...."
		try:
			db = MySQLdb.connect(host="192.185.4.111",
					 user="afy2003",
					  passwd="E4rmsrV+tw3r",
					  db="afy2003_BF")

			cur = db.cursor()
		except:
			print "RECONNECTION FAILED.. trying again in 60s"
			