from typing import IO
import logging
import uuid
import csv
import hashlib

from django.utils import timezone

from . import models
from . import ActionResult

logger = logging.getLogger(__name__)


class CsvFileExistsError(Exception):
    pass


class CsvFileValidationError(Exception):
    pass


class BookListCsvValidator:
    """Class will upload a CSV file object up to S3 Bucket and generate the DB Model to be saved with url,
    md5 hash, and file name, and can retrive the same file from S3 Bucket, based on DB Model input.
    """

    CSV_HEADERS = [
        "BOOK AUTHOR",
        "BOOK TITLE",
        "DATE PUBLISHED",
        "PUBLISHER NAME",
        "UNIQUE IDENTIFER",
    ]

    def __init__(
        self, s3_bucket_name: str = "jc1976bucket", aws_region_name: str = "eu-west-1"
    ):
        self.s3_bucket_name = s3_bucket_name
        self.aws_region_name = aws_region_name

    def _generate_file_name(self) -> str:
        return f"{str(uuid.uuid4())}.csv"

    def _generate_check_md5_checksum(self, file: IO) -> str:
        """Create MD5 Checksum of File Object and check it doesn't exist already.

        If it does exist then Throw error

        Args:
            file (IO): File like objecy of upload CSV

        Returns:
            str: md5 hexgest

        Raises:
            CsvFileExistsError: Existing File content already exists
        """
        file.seek(0)
        md5 = hashlib.md5()
        # handle content in binary form
        while chunk := file.read(4096):
            md5.update(chunk)
        md5_checksum = md5.hexdigest()

        if models.BookFile.objects.filter(md5_checksum=md5_checksum).exists():
            raise CsvFileExistsError("File already been upload to system")

        return md5_checksum

    def _validate_csv_file(self, file: IO) -> None:
        """Validate if the correct columns exist in csv file content.

        Args:
            file (IO): File like object of csv file.

        Raises:
            CsvFileValidationError: If validation errors found.
        """
        file.seek(0)
        reader = csv.DictReader(file.read().decode("utf-8").splitlines(True))
        fieldnames = sorted(list(map(lambda x: x.upper(), reader.fieldnames)))
        if self.CSV_HEADERS != fieldnames:
            raise CsvFileValidationError(
                f"CSV Column Headers were {sorted(reader.fieldnames)} and should be {self.CSV_HEADERS}!",
            )

    def _contruct_s3_url(self, file_name: str) -> str:
        return f"https://{self.s3_bucket_name}.s3.{self.aws_region_name}.amazonaws.com/{file_name}"

    def validate(self, file: IO) -> ActionResult:
        """Process basic validation of uploaded csv file

        Args:
            file (IO): _description_

        Returns:
            models.BookFile: _description_
        """
        action_result = ActionResult(True, None, None)
        try:
            # Do basic validation check before sending to celery
            md5 = self._generate_check_md5_checksum(file)
            file_name = self._generate_file_name()
            self._validate_csv_file(file)
            # reset file to start
            file.seek(0)
            # Build DB Object to return
            action_result.result_object = models.BookFile(
                file_name=file.name,
                s3_url=self._contruct_s3_url(file_name),
                date_uploaded=timezone.now(),
                md5_checksum=md5,
            )

        except (CsvFileExistsError, CsvFileValidationError) as e:
            return ActionResult(
                False, f"Failed to upload {file.name} due to validation - {e}.", None
            )
        except Exception as e:
            return ActionResult(
                False,
                f"Failed Unexpectedly to Upload {file.name} - {e}.",
                None,
            )
        return action_result
