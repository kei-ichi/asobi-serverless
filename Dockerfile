FROM ubuntu:latest
LABEL authors="kei-ichi"

ENTRYPOINT ["top", "-b"]