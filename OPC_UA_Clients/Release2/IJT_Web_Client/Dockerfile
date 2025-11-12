FROM nikolaik/python-nodejs:python3.13-nodejs24

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install requests python-dotenv nodeenv websockets asyncua packaging

ENV IS_DOCKER=true
ENV PYTHONUNBUFFERED=1

COPY . .

RUN npm cache clean --force

RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

RUN chmod +x setup_project.py

EXPOSE 3000 8001

CMD sh -c "npm ci || npm install --legacy-peer-deps && python setup_project.py --force_full && tail -f /dev/null"