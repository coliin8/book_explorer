from typing import Any, Dict, List, Tuple, IO, Callable
import uuid
import csv
import hashlib
import abc

from django.utils import timezone
import boto3
from botocore.client import ClientError

from . import models


class UploadFileManagerInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "upload")
            and callable(subclass.upload)
            and hasattr(subclass, "retrieve")
            and callable(subclass.retrieve)
            or NotImplemented
        )

    def _generate_file_name(self) -> str:
        return f"{str(uuid.uuid4())}.csv"

    def _create_csv_reader_from_file_object(self, file: IO) -> csv.DictReader:
        lines = file.read().decode("utf-8").splitlines(True)
        return csv.DictReader(lines)

    def _generate_md5_checksum(self, file: IO) -> str:
        file.seek(0)
        md5 = hashlib.md5()
        # handle content in binary form
        while chunk := file.read(4096):
            md5.update(chunk)
        return md5.hexdigest()

    def csv_file_object_to_dict(self, file: IO) -> Dict[str, List[Dict[str, Any]]]:
        reader = self._create_csv_reader_from_file_object(file)
        output = {"rows": []}
        for row in reader:
            output["rows"].append({header: row[header] for header in self.CSV_HEADERS})
        return output

    @abc.abstractmethod
    def upload(self, file: IO) -> models.BookFile:
        raise NotImplementedError

    @abc.abstractmethod
    def retrieve(self, file: models.BookFile) -> IO:
        """Extract text from the data set"""
        raise NotImplementedError


class S3UploadFileManager(UploadFileManagerInterface):
    """Class will upload a CSV file object up to S3 Bucket and generate the DB Model to be saved with url,
    md5 hash, and file name, and can retrive the same file from S3 Bucket, based on DB Model input.

    Subclass of UploadFileManagerInterface in case cloud storage changes, interface can stay the same.
    """

    CSV_HEADERS = [
        "Book Author",
        "Book title",
        "Date published",
        "Publisher name",
        "Unique identifer",
    ]

    def __init__(
        self, s3_bucket_name: str = "jc1976bucket", aws_region_name: str = "eu-west-1"
    ):
        self.client = boto3.client("s3")
        self.s3_bucket_name = s3_bucket_name
        self.aws_region_name = aws_region_name
        self._create_bucket()

    def _create_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.s3_bucket_name)
        except ClientError:
            self.client.create_bucket(
                Bucket=self.s3_bucket_name,
                CreateBucketConfiguration={"LocationConstraint": self.aws_region_name},
            )

    def _contruct_s3_url(self, file_name: str) -> str:
        return f"https://{self.s3_bucket_name}.s3.{self.aws_region_name}.amazonaws.com/{file_name}"

    def _validate_csv_file(self, file) -> Tuple[bool, str | None]:
        file.seek(0)
        reader = self._create_csv_reader_from_file_object(file)
        if sorted(reader.fieldnames) != self.CSV_HEADERS:
            return (
                False,
                f"CSV Column Headers were {sorted(reader.fieldnames)} and should be {self.CSV_HEADERS}!",
            )
        for row in reader:
            pass
        return (
            True,
            None,
        )

    def upload(self, file: IO) -> models.BookFile:
        md5 = self._generate_md5_checksum(file)
        file_name = self._generate_file_name()
        self._validate_csv_file(file)
        file.seek(0)
        self.client.upload_fileobj(file, self.s3_bucket_name, file_name)
        # Build DB Object to return
        return models.BookFile(
            file_name=file.name,
            s3_url=self._contruct_s3_url(file_name),
            date_uploaded=timezone.now(),
            md5_checksum=md5,
        )

    def retrieve(self, file: models.BookFile) -> IO:
        obj = self.client.get_object(
            Bucket=self.s3_bucket_name, Key=file.s3_url.split("/")[-1]
        )
        return obj["Body"]
