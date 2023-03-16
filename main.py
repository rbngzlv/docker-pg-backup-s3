#!/usr/bin/python3

from schedule import every, repeat, run_pending
from sh import pg_dump

import boto3
import functools
import gzip
import os
import time

# This decorator can be applied to any job function to log the elapsed time of each job
def print_elapsed_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_timestamp = time.time()
        print('LOG: Running job "%s"' % func.__name__)
        result = func(*args, **kwargs)
        print('LOG: Job "%s" completed in %d seconds' % (func.__name__, time.time() - start_timestamp))
        return result

    return wrapper

@repeat(every().day.at('02:00'))
@print_elapsed_time
def backup():
    print("     --> Generating a new backup ....")

    database_name = os.getenv('POSTGRES_DATABASE')
    timestr = time.strftime('%Y%m%d-%H%M%S')
    filename = f'backup-{timestr}-{database_name}.dump.gz'

    new_env = os.environ.copy()
    new_env["PGPASSWORD"] = os.getenv('POSTGRES_PASSWORD')

    with gzip.open(filename, "wb") as f:
        pg_dump(
            "-h", os.getenv('POSTGRES_HOST'),
            "-p", os.getenv('POSTGRES_PORT'),
            "-U", os.getenv('POSTGRES_USER'),
            "-d", database_name,
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
            "--column-inserts",
            "-Fc",
            _out=f,
            _env=new_env
        )
    
    print("     --> Backup completed, uploading to S3 ...")
    s3_client = boto3.client('s3',
        endpoint_url=os.getenv('S3_ENDPOINT'),
        aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY')
    )
    try:
        s3_client.upload_file(filename, os.getenv('S3_BUCKET'), os.getenv('S3_PREFIX') + '/' + filename)
        os.remove(filename)
    except boto3.exceptions.S3UploadFailedError as exc:
        print(exc)
        exit(1)

    print("     --> File successfully uploaded.")

while True:
    run_pending()
    time.sleep(1)
