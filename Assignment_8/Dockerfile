FROM python:3.7
ENV GOOGLE_APPLICATION_CREDENTIALS=./hartwelg-hw8-gae-801d5d0abde3.json
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE ${PORT}
CMD [ "python", "main.py" ]