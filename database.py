import mysql.connector
import myconfig as cfg

mydb = mysql.connector.connect(**cfg.mysql_remote)

# print(mydb)

mycursor = mydb.cursor()

mycursor.execute("SHOW DATABASES")

for x in mycursor:
  print(x)