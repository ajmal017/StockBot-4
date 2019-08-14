import sqlite3

conn = sqlite3.connect('users.db') #create user database
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users(uid)")
c.execute("INSERT INTO users(uid) VALUES('123456')")
