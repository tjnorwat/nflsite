import os 
import sqlite3


def restart():
    if os.path.exists('database.db'):
        os.remove('database.db')
    connection = sqlite3.connect('database.db')
    
    with open('schema.sql') as f:
        connection.executescript(f.read())


# no work
def addUser():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    conn.execute('INSERT INTO user (user_name, user_pass) VALUES (?, ?);',
                    ('guitars11', 'mypassword'))
    conn.commit()
    conn.close()

    
if __name__ == '__main__':
    #restart()

    addUser()
    