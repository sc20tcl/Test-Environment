import subprocess
import requests
import time
import subprocess
import re
import pandas as pd

prometheus_pod_query = 'avg(sum(rate(container_cpu_usage_seconds_total{namespace="default", pod=~"teastore-webui-.*", container!="POD", container!=""}[2m])) by (pod))' 
prometheus_node_query = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle", instance="10.224.0.4:9100"}[2m])) * 100)'
prometheus_url = 'http://4.158.172.106:9090'
replica_count = 1

stages = [
    {'rate': 100, 'duration': '300s', 'preAllocatedVUs': 100, 'maxVUs': 200},
    {'rate': 250, 'duration': '300s', 'preAllocatedVUs': 250, 'maxVUs': 500},
    {'rate': 500, 'duration': '300s', 'preAllocatedVUs': 500, 'maxVUs': 1000},
    {'rate': 750, 'duration': '300s', 'preAllocatedVUs': 750, 'maxVUs': 1500},
    {'rate': 1000, 'duration': '300s', 'preAllocatedVUs': 1000, 'maxVUs': 2000},
    {'rate': 1250, 'duration': '300s', 'preAllocatedVUs': 1250, 'maxVUs': 2500},
    {'rate': 1500, 'duration': '300s', 'preAllocatedVUs': 1500, 'maxVUs': 3000},
    {'rate': 1750, 'duration': '300s', 'preAllocatedVUs': 1750, 'maxVUs': 3500},
    {'rate': 2000, 'duration': '300s', 'preAllocatedVUs': 2000, 'maxVUs': 4000},
    {'rate': 2250, 'duration': '300s', 'preAllocatedVUs': 2250, 'maxVUs': 4500}
]

def query_prometheus(query):
    try:
        full_url = f"{prometheus_url}/api/v1/query"
        response = requests.get(full_url, params={'query': query})
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except requests.exceptions.RequestException as err:
        print(f"Error querying Prometheus: {err}")
    except ValueError as err:
        print(f"Error parsing JSON response: {err}")


def run_stage(stage):
    test_command = f"k6 run -e RATE={int(stage['rate']/3)} -e DURATION={stage['duration']} -e PREALLOCATED_VUS={int(stage['preAllocatedVUs'])} -e MAX_VUS={int(stage['maxVUs'])} ./k6Job.js"    
    print(f"Running stage: {test_command}")
    try:
        result = subprocess.run(test_command, check=True, shell=True, text=True, stdout=subprocess.PIPE)
        output = result.stdout
        print(output)
        
        fail_match = re.search(r"http_req_failed[^:]*: (\d+\.\d+)%", output)
        reqs_match = re.search(r"http_reqs[^:]*: (\d+)", output)
        duration_match95 = re.search(r"http_req_duration.*?p\(95\)=([^ ]*)", output) 
        duration_match90 = re.search(r"http_req_duration.*?p\(90\)=([^ ]*)", output)   
        if reqs_match:
            http_reqs = reqs_match.group(1)
            print(f"HTTP Requests: {http_reqs}")
        if duration_match95:
            http_req_duration_p95 = duration_match95.group(1)
            # print(f"HTTP Requests duration (95%): {http_req_duration_p95}")
        if duration_match90:
            http_req_duration_p90 = duration_match90.group(1)
            # print(f"HTTP Requests duration (90%): {http_req_duration_p90}")
        else:
            print("Failed to find the HTTP request duration in the output.")
            failed_rate = 6969
        if fail_match:
            failed_rate = fail_match.group(1)
            print(f"HTTP Requests Failed: {failed_rate}%")
        else:
            print("Failed to find the HTTP request failure rate in the output.")
            failed_rate = 6969
        print('Stage complete, querying Prometheus...')
        prometheus_pod_response = query_prometheus(prometheus_pod_query)
        print(prometheus_pod_response['data']['result'][0]['value'][1])
        prometheus_node_response = query_prometheus(prometheus_node_query)
        print(prometheus_node_response['data']['result'][0]['value'][1])
        return prometheus_pod_response['data']['result'][0]['value'][1], prometheus_node_response['data']['result'][0]['value'][1], failed_rate, http_reqs, http_req_duration_p90, http_req_duration_p95
    except subprocess.CalledProcessError as e:
        print(f'Error running k6 stage: {e}')



def scale_deployment(deployment_name, replicas, namespace="default"):
    try:
        command = ["kubectl", "scale", "deployment", deployment_name, "--replicas={}".format(replicas), "-n", namespace]
    
        subprocess.run(command, check=True)
        print(f"Deployment {deployment_name} scaled to {replicas} replicas in the '{namespace}' namespace.")
    
    except subprocess.CalledProcessError as e:
        print(f"Error scaling deployment: {e}")


def run_test(filepath, replica_array):
    data_array = []
    fail_limit = False
    

    for stage in stages:
        pod_response, node_response, failed_rate, http_reqs, http_req_duration_p90, http_req_duration_p95 = run_stage(stage)
        data_array.append([replicas, int(stage['rate']/3), pod_response, node_response, failed_rate, http_reqs, http_req_duration_p90, http_req_duration_p95])
        print("fail rate int: ", float(failed_rate))
        if float(failed_rate) > 10:
            fail_limit = True
            print(f"Failed test: {replicas} replicas {stage} stage")
            break
    print(data_array)
        
    headers = ["replicas", "virtual users", "pod response", "node response", "failed rate", "http reqs", "http req duration (90%)", "http req duration (95%)"]

    df = pd.DataFrame(data_array, columns=headers)
    df.to_csv(file_path, index=False)

    print(f"Data written to {file_path}")
    time.sleep(600)


with open("directory-test.txt", 'w') as file:
            file.write("This is a test file created by Python.\n")

replica_array = [2, 3, 4, 7]

for replicas in replica_array:
    print("replicas: ", replicas)
    scale_deployment("teastore-webui", replicas)
    print("5 minute cool down...")
    time.sleep(300)
    file_path = f'application_profile_{replicas}.csv'
    run_test(file_path, replica_array) 




