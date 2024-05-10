import subprocess
import requests
import time
import pandas as pd
import re

# Prometheus configurations
prometheus_url = 'http://172.165.91.160:9090'
prometheus_pod_query = 'avg(sum(rate(container_cpu_usage_seconds_total{namespace="default", pod=~"teastore-webui-.*", container!="POD", container!=""}[2m])) by (pod))'
prometheus_node_query = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle", instance="10.224.0.12:9100"}[1m])) * 100)'
pod_count_query = 'count(kube_pod_info{namespace="default", pod=~"teastore-webui-.*"}) by (namespace)'
last_minute_query = 'sum(rate(http_requests_total[1m]))'

def query_prometheus(query):
    """Query Prometheus using the HTTP API and return the JSON response."""
    try:
        full_url = f"{prometheus_url}/api/v1/query"
        response = requests.get(full_url, params={'query': query})
        response.raise_for_status()
        data = response.json()
        return data['data']['result']
    except requests.exceptions.RequestException as err:
        print(f"Error querying Prometheus: {err}")
        return None
    
def get_pods():
    command = 'kubectl get pods -n default -l "app=teastore,run=teastore-webui" --field-selector=status.phase=Running --no-headers | wc -l'
    try:
        result = subprocess.run(command, shell=True, text=True, stdout=subprocess.PIPE, check=True)
        pod_number = result.stdout.strip()  
        print(f"{pod_number} pods")
        return int(pod_number) 
    except subprocess.CalledProcessError as e:
        print(f"Error getting pods: {e}")
        return None

def run_stage(stage):
    """Run a k6 test stage."""
    test_command = f"k6 run -e RATE={int(stage['rate'])} -e DURATION={stage['duration']} -e PREALLOCATED_VUS={int(stage['preAllocatedVUs'])} -e MAX_VUS={int(stage['maxVUs'])} ./k6Job.js"
    print(f"Running stage with {int(stage['vus']/3)} virtual users for {stage['duration']}.")
    try:
        result = subprocess.run(test_command, check=True, shell=True, text=True, stdout=subprocess.PIPE)
        output = result.stdout

        fail_match = re.search(r"http_req_failed[^:]*: (\d+\.\d+)%", output)
        reqs_match = re.search(r"http_reqs[^:]*: (\d+)", output)
        duration_match95 = re.search(r"http_req_duration.*?p\(95\)=([^ ]*)", output) 
        duration_match90 = re.search(r"http_req_duration.*?p\(90\)=([^ ]*)", output)   
        if reqs_match:
            http_reqs = reqs_match.group(1)
            # print(f"HTTP Requests: {http_reqs}")
        if duration_match95:
            http_req_duration_p95 = duration_match95.group(1)
            # print(f"HTTP Requests duration (95%): {http_req_duration_p95}")
        if duration_match90:
            http_req_duration_p90 = duration_match90.group(1)
            # print(f"HTTP Requests duration (90%): {http_req_duration_p90}")
        if fail_match:
            failed_rate = fail_match.group(1)
        else:
            print("Failed to find the HTTP request failure rate in the output.")
            failed_rate = 6969
        try:
            pod_count = int(get_pods())
        except Exception as e:
            print(f"Error getting pod count: {e}")
            pod_count = None
        try:
            pod_cpu = float(query_prometheus(prometheus_pod_query)[0]['value'][1])
        except Exception as e:
            print(f"Error retrieving or parsing pod CPU data: {e}")
            pod_cpu = None
        try:
            node_cpu = float(query_prometheus(prometheus_node_query)[0]['value'][1]) / 100
        except Exception as e:
            print(f"Error retrieving or parsing node CPU data: {e}")
            node_cpu = None

        return pod_count, pod_cpu, node_cpu, failed_rate, http_reqs, http_req_duration_p90, http_req_duration_p95
    except subprocess.CalledProcessError as e:
        print(f'Error running k6 stage: {e}')
        return 'Test failed'


data = pd.read_csv("../ValidateData.csv", parse_dates=['period'], index_col='period')

data_array = [data['1998-06-24 13:44:00': '1998-06-24 14:49:00'], data['1998-06-24 16:47:00': '1998-06-24 17:52:00'], data['1998-06-24 15:57:00': '1998-06-24 17:02:00'], data['1998-06-24 16:47:00': '1998-06-24 17:52:00']]

warm_up = 0

for i in range(len(data_array)):
    test_data = []
    warm_up = 0
    for period, row in data_array[i].iterrows():
        warm_up += 1
        stage = {'rate': row['count']/(60 * 3), 'duration': '60s', 'preAllocatedVUs': row['count']/(60 * 3), 'maxVUs': row['count']/(60 * 1.5)},  # Run each stage for 1 minute
        print(f"Scheduling test for {stage['vus']} virtual users at {period}.")
        pod_count, pod_cpu, node_cpu, failed_rate, http_reqs, http_req_duration_p90, http_req_duration_p95 = run_stage(stage)
        if warm_up > 4:
            print([i, int(row['count']/60), pod_count, pod_cpu, node_cpu, failed_rate])
            test_data.append([i, int(row['count']/60), pod_count, pod_cpu, node_cpu, failed_rate, http_reqs, http_req_duration_p90, http_req_duration_p95])

    results_df = pd.DataFrame(test_data, columns=['Test Number','QPM', 'Pod Count', 'avg Pod CPU Usage', 'Node CPU Usage', 'Fail Rate', "http reqs", "http req duration (90%)", "http req duration (95%)"])
    results_df.to_csv(f'hpa_test_results{i}_2.csv', index=False)
    print(f"Test results saved to 'test_results{i}.csv'.")
