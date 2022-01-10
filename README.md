docker build --tag nfl-site-docker .
docker run -d -p 80:80 nfl-site-docker