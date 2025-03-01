from dagster import resource
import requests

class DagsterClient:
    """Client to interact with Dagster GraphQL API"""
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.graphql_endpoint = f"http://{host}:{port}/graphql"
    
    def execute_job(self, job_name):
        """Execute a job by name using GraphQL API"""
        mutation = """
        mutation ExecuteJob($jobName: String!) {
          launchPipelineExecution(
            executionParams: {
              selector: {
                pipelineName: $jobName
              },
              mode: "default"
            }
          ) {
            __typename
            ... on LaunchPipelineExecutionSuccess {
              run {
                runId
                status
              }
            }
            ... on PythonError {
              message
              stack
            }
          }
        }
        """
        
        variables = {
            "jobName": job_name
        }
        
        response = requests.post(
            self.graphql_endpoint,
            json={"query": mutation, "variables": variables}
        )
        
        return response.json()

@resource
def dagster_client_resource(context):
    """Resource for interacting with Dagster API"""
    return DagsterClient(
        host=context.resource_config.get("host", "localhost"),
        port=context.resource_config.get("port", 3000)
    )