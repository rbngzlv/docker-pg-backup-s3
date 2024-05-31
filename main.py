#!/usr/bin/python3

import boto3
import functools
import gzip
import shutil
import subprocess
import os
import time

from schedule import every, repeat, run_pending


def compress_file(file_name):
    print(f"     --> Compressing {file_name} ....")
    compressed_file_name = "{}.gz".format(str(file_name))
    with open(file_name, 'rb') as f_in:
        with gzip.open(compressed_file_name, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(file_name)
    return compressed_file_name

def upload_to_s3(file_name):
    print(f"     --> Uploading {file_name} to S3 ...")
    s3_client = boto3.client('s3',
        endpoint_url=os.getenv('S3_ENDPOINT'),
        aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY')
    )
    try:
        s3_client.upload_file(file_name, os.getenv('S3_BUCKET'), os.getenv('S3_PREFIX') + '/' + file_name)
        os.remove(file_name)
    except boto3.exceptions.S3UploadFailedError as exc:
        print(exc)
        exit(1)

    print("     --> File successfully uploaded.")

def backup_database(host, name, port, user, password, filename, format="c"):
    print(f"     --> Generating a new backup (format: {format}) ....")

    args = [
                "pg_dump",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", name,
                "--no-owner",
                "--no-privileges",
                "--clean",
                "--if-exists",
                "--format", format,
                "--file", filename
            ]
    
    if format == "p":
        args.append("--column-inserts")

    try:
        process = subprocess.Popen(
            args,
            env={"PGPASSWORD": password},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        output, error = process.communicate()
        if int(process.returncode) != 0:
            print('Command failed. Return code : {}'.format(process.returncode))
            for line in output.splitlines():
                print(line)
            for line in error.splitlines():
                print(line)
            exit(1)
    except Exception as exc:
        print(exc)
        exit(1)
  
    print("     --> Backup completed")

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
    timestr = time.strftime('%Y%m%d-%H%M%S')
    db_name = os.getenv('POSTGRES_DATABASE')
    db_host = os.getenv('POSTGRES_HOST')
    db_port = os.getenv('POSTGRES_PORT')
    db_user = os.getenv('POSTGRES_USER')
    db_password = os.getenv('POSTGRES_PASSWORD')

    filename = f'backup-{timestr}-{db_name}.dump'
    backup_database(db_host, db_name, db_port, db_user, db_password, filename, format='c')
    upload_to_s3(compress_file(filename))

    filename = f'backup-{timestr}-{db_name}.sql'
    backup_database(db_host, db_name, db_port, db_user, db_password, filename, format='p')
    upload_to_s3(compress_file(filename))

while True:
    run_pending()
    time.sleep(1)
