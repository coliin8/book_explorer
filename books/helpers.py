import datetime
import time
import csv
import json
import logging
from typing import IO, Dict, List

from celery.result import AsyncResult

from . import ActionResult

logger = logging.getLogger(__name__)


def check_csv_upload_state_helper(
    async_result: AsyncResult, seconds: int
) -> ActionResult:
    """Check Async Result to determine what should be done.

    Args:
        book_file (AsyncResult): Task Async Resultto check

    Returns:
        ActionResult: Details of out come of action
    """
    result = ActionResult(True, None, None)
    endTime = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    while not datetime.datetime.now() >= endTime:
        result = ActionResult(True, None, None)
        match async_result.state:
            case "FAILURE" | "REVOKED":
                result.is_success = False
                result.message = str(async_result.info)
                # Probably consider delete entry and asking user to upload again.
            case "PENDING" | "RECEIVED" | "STARTED" | "RETRY":
                result.message = async_result.state
            case "SUCCESS":
                result.result_object = async_result.get()
                break
        time.sleep(0.5)
    return result


def convert_csv_to_dict_helper(file: IO) -> Dict[str, List[Dict[str, str]]]:
    """Convert File like object into

    Args:
        file (IO): _description_

    Returns:
        Dict[str, List[Dict[str, str]]]: _description_
    """
    logger.info(f"Generating JSON from CSV file {file}")
    reader = csv.DictReader(file.read().decode("utf-8").splitlines(True))
    output = {"rows": []}
    for row in reader:
        output["rows"].append(row)
    return output


def convert_dict_to_csv_helper(
    in_mem_file: IO, csv_json: Dict[str, List[Dict[str, str]]]
) -> str:
    """Convert Json representation of CSV content into in memory CSV file and return file content.

    Args:
        in_mem_file (IO): This is likely to be StringIO
        csv_json (Dict[str, List[Dict[str, str]]]): Json Representation of CSV

    Returns:
        Any: Content of an in-memory CSV file.
    """
    rows = csv_json["rows"]
    data = json.loads(json.dumps(rows))
    writer = csv.DictWriter(in_mem_file, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return in_mem_file.getvalue()
