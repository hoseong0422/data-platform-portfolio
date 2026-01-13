import pendulum
from classes.task import Task
from classes.embulk_k8s_task_factory import EmbulkDagFactory

KST = pendulum.timezone("Asia/Seoul")

dag, done_gate = EmbulkDagFactory.create_dag(
    dag_id='daily_jobs',
    schedule='10 0 * * *', # interval
    start_date=pendulum.datetime(2025, 10, 16, tz=KST),
    dataset_info=[
        {
            'manager': Task(__file__),
            'dataset': 'airflow_test',
            'prefix': ''
        }
    ],
    slack_conn_id='slack-alert-channel',
    db_secret_name='db-credentials',  # Secret 이름 지정
    db_mount_path='/var/secrets/db',  # 마운트 경로 지정
    tags=['embulk', 'daily']
)