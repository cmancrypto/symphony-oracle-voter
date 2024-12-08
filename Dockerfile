ARG BUILDPLATFORM="linux/amd64"

FROM ghcr.io/pfc-developer/heighliner/symphony:v0.4.1 AS symphony
FROM --platform=${BUILDPLATFORM} python:3-bookworm
LABEL org.opencontainers.image.description="Symphony blockchain price feeder"
LABEL org.opencontainers.image.source=https://github.com/cmancrypto/symphony-oracle-voter


WORKDIR /symphony
COPY --from=symphony /bin/symphonyd /usr/local/bin

COPY . .
RUN pip install -r ./requirements.txt 
RUN chmod 755 /symphony/oracle.sh
ENV VALIDATOR_ADDRESS=symphonyvaloperxxx
ENV VALIDATOR_ACC_ADDRESS=symphonyxxx
# - you need to delegate feeder to use this
ENV FEEDER_ADDRESS=symphonyxxx

ENV FEEDER_SEED=""

#ONLY FOR TELEGRAM NOTIFICATIONS DELETE OTHERWISE
ENV TELEGRAM_TOKEN=
ENV TELEGRAM_CHAT_ID=
# MATCH YOUR ACTUAL LCD PORT
ENV SYMPHONY_LCD=http://localhost:1317 
# your actual tendermint RPC address%
ENV TENDERMINT_RPC=tcp://localhost:26657 

ENV PYTHON_ENV=production
ENV LOG_LEVEL=INFO
ENV DEBUG=false

EXPOSE 19000
CMD ["/symphony/oracle.sh"]
#CMD ["/usr/local/bin/python","/symphony/main.py"]