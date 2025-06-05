
from app.utils.exceptions.tests_results_exceptions import KCIDBSubmitionException
from typing_extensions import Self
from datetime import datetime, UTC
from app.core.config import settings
from abc import ABC, abstractmethod
import requests
import logging
import kcidb
import yaml
import os


class KCITestResultsSubmitter:

    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), "kcidb.yml")
        with open(config_path, "r") as f:
            config_file = yaml.safe_load(f)
        self.__version_major = config_file["kcidb"]["major"]
        self.__version_minor = config_file["kcidb"]["minor"]
        self.__debug = settings.DEBUG


    def submit(self, tests):
        logging.info(f"Submitting tests: {tests}")
        report = {
            "tests": tests,
            "version": {
                "major": self.__version_major,
                "minor": self.__version_minor
            }
        }
        if self.__debug:
            logging.info(report)
        else:
            kcidb.io.SCHEMA.validate(report)
            requests.post(settings.KCIDB_SUBMIT_URL, headers={
                "Authorization": f"Bearer {settings.KCIDB_TOKEN}"
            }, json=report)


class KCIDBSubmission(ABC):
    _origin = "riscv"

    @abstractmethod
    def to_json(self):
        ...


class KCIDBTestSubmission(KCIDBSubmission):

    def __init__(self, test: str, path: str, result: str, log: str, test_id: str, build_id: str, started_at: datetime, runner: str, platform: str) -> Self:
        self.__test_id = test_id
        self.__build_id = build_id
        self.__path = path
        self.__result = result
        self.__started_at = started_at
        self.__log = log
        self.__test = test
        self.__runner = runner
        self.__platform = platform

    @property
    def test(self):
        return self.__test

    def to_json(self):
        return {
                "id": f"{self._origin}:{self.__test_id}",
                "build_id": self.__build_id,
                "origin": self._origin,
                "status": self.__result,
                "path": self.__path,
                "start_time": self.__started_at.astimezone(UTC).replace(microsecond=0).isoformat(),
                "environment": {
                    "misc": {
                        "platform": self.__platform,
                    }
                },
                "misc": {
                    "runtime": self.__runner,
                }
            }


class KCIDBuildSubmission(KCIDBSubmission):

    def __init__(self, build_id: str, valid: bool, arch: str, compiler: str, start_time: datetime) -> Self:
        self.__build_id = build_id
        self.__valid = valid
        self.__arch = arch
        self.__compiler = compiler
        self.__start_time = start_time
    

    def to_json(self):
        return {
                "id": f"{self._origin}:{self.__build_id}",
                "valid": self.__valid,
                "origin": self._origin,
                "architecture": self.__arch,
                "compiler": self.__compiler,
                "start_time": self.__start_time.astimezone(UTC).replace(microsecond=0).isoformat(),
            }

_submitter = KCITestResultsSubmitter()


def submit_kcidb(tests: list[dict]):
    try:
        if len(tests) == 0:
            logging.info("Got an empty list of tests, skipping submission")
            return
        _submitter.submit(tests)
    except Exception as e:
        logging.error(f"Could not validate submission!: {str(e)}")
        raise KCIDBSubmitionException()