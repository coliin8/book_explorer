# import json
# from typing import Any, Dict, List, IO
# import uuid
# import csv
# import hashlib
# import abc
# import logging

# from django.utils import timezone
# import boto3
# from botocore.client import ClientError

# from . import models
# from . import tasks

# logger = logging.getLogger(__name__)


# class CsvFileExistsError(Exception):
#     pass


# class CsvFileValidationError(Exception):
#     pass


# class UploadFileManagerInterface(metaclass=abc.ABCMeta):
#     """Abstract Class incase we want to change Cloud Provider.
#     Ok might be a bit overkill...
#     """

#     @classmethod
#     def __subclasshook__(cls, subclass):
#         return (
#             hasattr(subclass, "upload")
#             and callable(subclass.upload)
#             and hasattr(subclass, "retrieve")
#             and callable(subclass.retrieve)
#             or NotImplemented
#         )

#     def _generate_file_name(self) -> str:
#         return f"{str(uuid.uuid4())}.csv"

#     def _create_csv_reader_from_file_object(self, file: IO) -> csv.DictReader:
#         """Create csv Dict Reader

#         Args:
#             file (IO): File like object of CSV file.

#         Returns:
#             csv.DictReader: Dict Reader
#         """
#         lines = file.read().decode("utf-8").splitlines(True)
#         return csv.DictReader(lines)

#     def _generate_check_md5_checksum(self, file: IO) -> str:
#         """Create MD5 Checksum of File Object and check it doesn't exist already.

#         If it does exist then Throw error

#         Args:
#             file (IO): File like objecy of upload CSV

#         Returns:
#             str: md5 hexgest

#         Raises:
#             CsvFileExistsError: Existing File content already exists
#         """
#         file.seek(0)
#         md5 = hashlib.md5()
#         # handle content in binary form
#         while chunk := file.read(4096):
#             md5.update(chunk)
#         md5_checksum = md5.hexdigest()

#         if models.BookFile.objects.filter(md5_checksum=md5_checksum).exists():
#             raise CsvFileExistsError("File already been upload to system.")

#         return md5_checksum

#     def csv_file_object_to_dict(self, file: IO) -> Dict[str, List[Dict[str, str]]]:
#         """Convert File like object into

#         Args:
#             file (IO): _description_

#         Returns:
#             Dict[str, List[Dict[str, str]]]: _description_
#         """
#         logger.info(f"Generating JSON from CSV file {file}")
#         reader = self._create_csv_reader_from_file_object(file)
#         output = {"rows": []}
#         for row in reader:
#             output["rows"].append(row)
#         return output

#     def json_to_csv_output(
#         self, in_mem_file: IO, csv_json: Dict[str, List[Dict[str, str]]]
#     ) -> Any:
#         """Convert Json representation of CSV content into in memory CSV file and return file content.

#         Args:
#             in_mem_file (IO): This is likely to be StringIO
#             csv_json (Dict[str, List[Dict[str, str]]]): Json Representation of CSV

#         Returns:
#             Any: Content of an in-memory CSV file.
#         """
#         rows = csv_json["rows"]
#         data = json.loads(json.dumps(rows))
#         writer = csv.DictWriter(in_mem_file, fieldnames=rows[0].keys())
#         writer.writeheader()
#         writer.writerows(data)
#         return in_mem_file.getvalue()

#     @abc.abstractmethod
#     def upload(self, file: IO) -> models.BookFile:
#         raise NotImplementedError

#     @abc.abstractmethod
#     def retrieve(self, file: models.BookFile) -> IO:
#         """Extract text from the data set"""
#         raise NotImplementedError


# class S3UploadFileManager(UploadFileManagerInterface):
#     """Class will upload a CSV file object up to S3 Bucket and generate the DB Model to be saved with url,
#     md5 hash, and file name, and can retrive the same file from S3 Bucket, based on DB Model input.

#     Subclass of UploadFileManagerInterface in case cloud storage changes, interface can stay the same.
#     """

#     CSV_HEADERS = [
#         "BOOK AUTHOR",
#         "BOOK TITLE",
#         "DATE PUBLISHED",
#         "PUBLISHER NAME",
#         "UNIQUE IDENTIFER",
#     ]

#     def __init__(
#         self, s3_bucket_name: str = "jc1976bucket", aws_region_name: str = "eu-west-1"
#     ):
#         self.client = boto3.client("s3")
#         self.s3_bucket_name = s3_bucket_name
#         self.aws_region_name = aws_region_name
#         self._check_create_bucket()

#     def _check_create_bucket(self):
#         """Check if bucket exists, if it does then create it"""
#         try:
#             self.client.head_bucket(Bucket=self.s3_bucket_name)
#         except ClientError:
#             self.client.create_bucket(
#                 Bucket=self.s3_bucket_name,
#                 CreateBucketConfiguration={"LocationConstraint": self.aws_region_name},
#             )

#     def _contruct_s3_url(self, file_name: str) -> str:
#         return f"https://{self.s3_bucket_name}.s3.{self.aws_region_name}.amazonaws.com/{file_name}"

#     def _validate_csv_file(self, file: IO) -> None:
#         """Validate if the correct columns exist in csv file content.

#         Args:
#             file (IO): File like object of csv file.

#         Raises:
#             CsvFileValidationError: If validation errors found.
#         """
#         file.seek(0)
#         reader = self._create_csv_reader_from_file_object(file)
#         fieldnames = sorted(list(map(lambda x: x.upper(), reader.fieldnames)))
#         if self.CSV_HEADERS != fieldnames:
#             raise CsvFileValidationError(
#                 f"CSV Column Headers were {sorted(reader.fieldnames)} and should be {self.CSV_HEADERS}!",
#             )

#     def upload(self, file: IO) -> models.BookFile:
#         """Take in File uploaded in Book Explorer, validates its content is different to existing files using md5,
#         then

#         Args:
#             file (IO): File like Object

#         Returns:
#             models.BookFile: Book list file object of new file uploading to S3.
#         """
#         # Do basic validation check before sending to celery
#         md5 = self._generate_check_md5_checksum(file)
#         file_name = self._generate_file_name()
#         self._validate_csv_file(file)
#         file.seek(0)
#         # Build DB Object to return
#         db_book_file = models.BookFile(
#             file_name=file.name,
#             s3_url=self._contruct_s3_url(file_name),
#             date_uploaded=timezone.now(),
#             md5_checksum=md5,
#         )
#         logger.info(
#             f"Attempting to upload {file.name} to AWS S3 bucket {self.s3_bucket_name} as file called {file_name}."
#         )
#         # Now use Celery to do upload to S3
#         result = tasks.task_upload_to_cloud.delay(
#             self.aws_region_name,
#             self.s3_bucket_name,
#             file_name,
#             self.csv_file_object_to_dict(file),
#         )
#         db_book_file.async_task_id = result.task_id
#         return db_book_file

#     def retrieve(self, file: models.BookFile) -> IO:
#         """Retrieve CSV file from

#         Args:
#             file (models.BookFile): _description_

#         Returns:
#             IO: _description_
#         """
#         try:
#             obj = self.client.get_object(
#                 Bucket=self.s3_bucket_name, Key=file.s3_url.split("/")[-1]
#             )
#             return obj["Body"]
#         except ClientError as e:
#             # Check for specific things that will mean a complete failure.
#             raise e
