from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.kubernetes.secret import Secret
from kubernetes.client import models as k8s
import pendulum

KST = pendulum.timezone("Asia/Seoul")

CUSTOM_EMBULK_IMAGE=Variable.get("EMBULK_IMAGE").strip() # 개행 제거

MYSQL     = Secret(deploy_type="volume", deploy_target="/var/secrets/mysql", secret="mysql-credentials")
BIGQUERY  = Secret(deploy_type="volume", deploy_target="/var/secrets/bq", secret="bq-sa-key")

BQ_KEY_PATH = "/var/secrets/bq/key.json"

cmd = r"""
set -eu

# 파일에서 읽어서 이 프로세스에만 환경변수 설정 (Pod ENV에 노출 안 됨)
export DB_HOST="$(cat /var/secrets/mysql/host)"
export DB_PORT="$(cat /var/secrets/mysql/port)"
export DB_USER="$(cat /var/secrets/mysql/user)"
export DB_PASSWORD="$(cat /var/secrets/mysql/password)"
export DB_DATABASE="$(cat /var/secrets/mysql/database)"

# Embulk 실행 (config.yml.liquid가 env.*를 읽음)
embulk run /app/config/job.yml.liquid
"""

embulk_config_volume = k8s.V1Volume(
    name="embulk-config-volume",
    config_map=k8s.V1ConfigMapVolumeSource(
        name="embulk-config",
        items=[
            k8s.V1KeyToPath(
                key="job.yml.liquid",       # ConfigMap의 key
                path="job.yml.liquid"  # 컨테이너 안에서 보일 파일명
                )
            ],
        ),
    )
    
embulk_config_volume_mount = k8s.V1VolumeMount(
    name="embulk-config-volume",
    mount_path="/app/config",
    read_only=True
    )

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'email': ["hoseong0422@gmail.com"],
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}  

tables = ['nomal_resource_table_a', 'nomal_resource_table_b', 'himem_reousrce_table_a', 'himem_reousrce_table_b']
himem_limit_tables = ['himem_reousrce_table_a', 'himem_reousrce_table_b']

nomal_limit = {"cpu": 1, "memory": "1Gi"}
himem_limit = {"cpu": 2.5, "memory": "3Gi"}

with DAG(
    'db-to-bq',
    default_args=default_args,
    description='mysql db의 테이블을 BigQuery에 적재',
    start_date=pendulum.datetime(2025, 10, 16, tz=KST),
    schedule='10 3 * * *', # 매일 KST 03:10
    max_active_tasks=6,
    catchup=False,
    tags=['embulk', 'mysql', 'daily', '3 AM', 'sharding'],
    ) as dag:

    tasks = []
    
    for table in tables:
        task = KubernetesPodOperator(
            task_id=f'{table}_to_bq',
            name=f'{table}_to_bq',
            base_container_name=f'{table.replace('_', '-') if len(table) <= 40 else table[-40:].replace('_', '-')}-to-bq-job-container',
            namespace='airflow',
            is_delete_operator_pod=True,
            image=CUSTOM_EMBULK_IMAGE,
            image_pull_policy='IfNotPresent',
            cmds=["/bin/sh", "-c"],
            arguments=[cmd],
            secrets=[MYSQL, BIGQUERY],
            env_vars={
                    "DB_QUERY": (
                        "SELECT * "
                        f"FROM {table} "
                        "WHERE created_at >= '{{ data_interval_start.in_timezone(\'Asia/Seoul\') | ds }} 00:00:00' AND created_at < '{{ data_interval_end.in_timezone(\'Asia/Seoul\') | ds }} 00:00:00'"
                        ),
                    "BQ_MODE": "replace",
                    "BQ_DATASET": "airflow_test",
                    "BQ_TABLE": (
                        f"{table}_"
                        "{{ data_interval_start.in_timezone(\'Asia/Seoul\') | ds_nodash }}"
                        ),
                    "BQ_KEY_PATH": BQ_KEY_PATH
                },
            get_logs=True,
            in_cluster=True,
            log_events_on_failure=True,
            retry_delay=timedelta(minutes=2),
            startup_timeout_seconds=300,
            container_resources=k8s.V1ResourceRequirements(
                requests={"cpu": 1, "memory": "1Gi"},
                limits=nomal_limit if table not in himem_limit_tables else himem_limit
            ),
            volumes=[
                embulk_config_volume
            ],
            volume_mounts=[
                embulk_config_volume_mount
            ]
        )

        tasks.append(task)


    tasks
