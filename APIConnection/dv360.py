import socket
import argparse
import os
import pprint
import httplib2
import sys

import pandas as pd
from datetime import datetime
from datetime import timedelta
from contextlib import closing
from six.moves.urllib.request import urlopen

from google.api_core import retry
from googleapiclient import discovery
from oauth2client.file import Storage
from oauth2client import tools, client
from oauth2client.service_account import ServiceAccountCredentials

sys.path.insert(0, os.path.abspath(".."))

from APIConnection.config import dv360_config
from APIConnection.logger import get_logger

# logger = get_logger(
#     "dv360", file_name=dv360_config.LOG_FILE, log_level=dv360_config.LOG_LEVEL
# )
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

class DV360(object):
    _API_NAME = "displayvideo"
    _DEFAULT_API_VERSION = "v1"
    _API_SCOPES = [
        "https://www.googleapis.com/auth/doubleclickbidmanager",
        "https://www.googleapis.com/auth/display-video",
    ]
    _API_URL = "https://displayvideo.googleapis.com/"
    _REPORT_EXT = ".csv"

    def __init__(
        self, cred="", date_range="", output="", frequency="", report_window=None
    ):
        if date_range:
            self.REPORT_DATE_RANGE = date_range
        else:
            self.REPORT_DATE_RANGE = "LAST_7_DAYS"
        self.CREDENTIALS_FILE = cred
        self.REPORT_OUTPUT_DIR = output
        self.REPORT_FREQUENCY = frequency
        self.REPORT_WINDOW = report_window

    @staticmethod
    def get_arguments(argv, desc, parents=None):
        """Validates and parses command line arguments.

        Args:
          argv: list of strings, the command-line parameters of the application.
          desc: string, a description of the sample being executed.
          parents: list of argparsers, the argparsers passed in by the method calling this function.

        Returns:
          The parsed command-line arguments.
        """
        parser = argparse.ArgumentParser(
            description=desc,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            parents=parents,
        )
        return parser.parse_args(argv[1:])

    def authenticate_using_user_account(self):
        """Steps through Service Account OAuth 2.0 flow to retrieve credentials."""
        flow = client.flow_from_clientsecrets(
            self.CREDENTIALS_FILE, scope=self._API_SCOPES
        )
        # Check whether credentials exist in the credential store. Using a credential
        # store allows auth credentials to be cached, so they survive multiple runs
        # of the application. This avoids prompting the user for authorization every
        # time the access token expires, by remembering the refresh token.
        storage = Storage(dv360_config.CREDENTIAL_STORE_FILE)
        credentials = storage.get()

        # If no credentials were found, go through the authorization process and
        # persist credentials to the credential store.
        if credentials is None or credentials.invalid:
            credentials = tools.run_flow(
                flow, storage, tools.argparser.parse_known_args()[0]
            )

        # Use the credentials to authorize an httplib2.Http instance.
        http = credentials.authorize(httplib2.Http())

        return http

    def authenticate_using_service_account(self, impersonation_email=""):
        """Authorizes an httplib2.Http instance using service account credentials."""
        # Load the service account credentials from the specified JSON keyfile.
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            dv360_config.SERVICE_ACCOUNT_CREDS, scopes=self._API_SCOPES
        )

        # Configure impersonation (if applicable).
        if impersonation_email:
            credentials = credentials.create_delegated(impersonation_email)

        # Use the credentials to authorize an httplib2.Http instance.
        http = credentials.authorize(httplib2.Http())

        return http

    def build_discovery_url(self, version, label, key):
        """Builds a discovery url from which to fetch the proper discovery document.

        Args:
          version: a str indicating the version number of the API.
          label: a str indicating a label to be applied to the discovery service request. This may be used
            as a means of programmatically retrieving a copy of a discovery document containing
            allowlisted content.
          key: a str generated by the user project attempting to retrieve this discovery document.

        Returns:
          A str that can be used to retrieve the disovery document for the API version given.
        """
        discovery_url = f"{self._API_URL}/$discovery/rest?version={version}"
        if label:
            discovery_url = discovery_url + f"&labels={label}"
        if key:
            discovery_url = discovery_url + f"&key={key}"
        return discovery_url

    def get_service(self, version=_DEFAULT_API_VERSION, label=None, key=None):
        """Builds the Display & Video 360 API service used for the REST API.

        Args:
          version: a str indicating the Display & Video 360 API version to be
            retrieved.
          label: a str indicating a label to be applied to the discovery service request. This may be used
            as a means of programmatically retrieving a copy of a discovery document containing
            allowlisted content.
          key: a str identifying the user project.

        Returns:
          A googleapiclient.discovery.Resource instance used to interact with the Display & Video 360 API.
        """
        http = self.authenticate_using_user_account()

        discovery_url = self.build_discovery_url(version, label, key)

        socket.setdefaulttimeout(180)

        # Initialize client for Display & Video 360 API
        dv360_service = discovery.build(
            self._API_NAME, version, discoveryServiceUrl=discovery_url, http=http
        )

        dbm_service = discovery.build("doubleclickbidmanager", "v1.1", http=http)

        return dbm_service, dv360_service

    def create_report(self, dbm_service, dv360_service):
        # Define DV360 report definition (i.e. metrics and filters)
        # List of official supported metrics and filter groups can be found in following url:
        # https://developers.google.com/bid-manager/v1.1/filters-metrics
        report_definition = {
            "params": {
                "type": dv360_config.REPORT_TYPE,
                "metrics": dv360_config.REPORT_METRICS,
                "groupBys": dv360_config.REPORT_FILTER_GROUP,
                "filters": [],
            },
            "metadata": {
                "title": dv360_config.REPORT_TITLE,
                "dataRange": self.REPORT_DATE_RANGE,
                "format": dv360_config.REPORT_FORMAT,
            },
            "schedule": {"frequency": self.REPORT_FREQUENCY},
        }

        # Create new query using report definition
        try:
            operation = (
                dbm_service.queries().createquery(body=report_definition).execute()
            )
            return operation["queryId"]
        except Exception as e:
            raise e

    def get_full_report(self, dbm_service, query_id):
        if query_id:
            # Runs the given Queries.getquery request, retrying with an exponential
            # backoff. Returns completed operation. Will raise an exception if the
            # operation takes more than five hours to complete.
            @retry.Retry(
                predicate=retry.if_exception_type(Exception),
                initial=5,
                maximum=60,
                deadline=18000,
            )
            def check_get_query_completion(getquery_request):
                """Queries metadata to check for completion."""
                completion_response = getquery_request.execute()
                if completion_response["metadata"]["running"]:
                    raise Exception("The operation has not completed.")
                return completion_response

            # Call the API, getting the latest status for the passed queryId.
            getquery_request = dbm_service.queries().getquery(queryId=query_id)
            query = check_get_query_completion(getquery_request)
            try:
                now = datetime.now()  # current date and time
                date_time = now.strftime("%Y_%m_%d-%H%M%S")
                report_filename = date_time + self._REPORT_EXT
                report_output_file = os.path.join(
                    self.REPORT_OUTPUT_DIR, report_filename
                )
                os.system(f"mkdir -p {self.REPORT_OUTPUT_DIR}")
                # If it is recent enough...
                if self.is_in_report_window(
                    query["metadata"]["latestReportRunTimeMs"], self.REPORT_WINDOW
                ):

                    # Grab the report and write contents to a file.
                    report_url = query["metadata"][
                        "googleCloudStoragePathForLatestReport"
                    ]
                    with open(report_output_file, "wb") as output:
                        with closing(urlopen(report_url)) as url:
                            output.write(url.read())
                    logger.info("Download complete.")
                else:
                    logger.error(
                        f"No reports for queryId {query['queryId']} in the last {self.REPORT_WINDOW} hours."
                    )
            except KeyError:
                logger.error('No report found for queryId "%s".' % query_id)
        else:
            raise "Query ID must not be none"

    @staticmethod
    def is_in_report_window(run_time_ms, report_window):
        """Determines if the given time in milliseconds is in the report window.

        Args:
          run_time_ms: str containing a time in milliseconds.
          report_window: int identifying the range of the report window in hours.

        Returns:
          A boolean indicating whether the given query's report run time is within
          the report window.
        """
        report_time = datetime.fromtimestamp(int((run_time_ms)) / 1000)
        earliest_time_in_range = datetime.now() - timedelta(hours=report_window)
        return report_time > earliest_time_in_range


if __name__ == "__main__":
    # Retrieve command line arguments.
    # flags = samples_util.get_arguments(sys.argv, __doc__, parents=[argparser])

    dv360 = DV360()
    dbm_service_object, dv360_service_object = dv360.get_service(version="v1")
    dv360.create_report(dbm_service_object, dv360_service_object)
