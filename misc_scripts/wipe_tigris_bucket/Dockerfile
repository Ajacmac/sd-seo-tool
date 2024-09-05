FROM alpine:3.18

# Install AWS CLI
RUN apk add --no-cache \
        python3 \
        py3-pip \
    && pip3 install --upgrade pip \
    && pip3 install --no-cache-dir awscli

# Create a non-root user
RUN adduser -D awsuser
USER awsuser
WORKDIR /home/awsuser

# Script to empty the bucket
COPY --chown=awsuser:awsuser empty_bucket.sh .
RUN chmod +x empty_bucket.sh

ENTRYPOINT ["./empty_bucket.sh"]