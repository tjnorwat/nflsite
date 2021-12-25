from nflsite import app
from waitress import serve

if __name__ == '__main__':
    #app.run(host='localhost', port=80, debug=True)
    serve(app, host='0.0.0.0', port=80, url_scheme='http', threads=20)