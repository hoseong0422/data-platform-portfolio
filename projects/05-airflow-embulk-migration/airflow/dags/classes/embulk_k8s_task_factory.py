from datetime import timedelta
import requests
import pendulum
from datetime import timedelta
from airflow.hooks.base import BaseHook
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook
from airflow.models import Variable
from airflow.kubernetes.secret import Secret
from airflow.operators.empty import EmptyOperator
from kubernetes.client import models as k8s


class EmbulkDagFactory:
    KST = pendulum.timezone("Asia/Seoul")
    CUSTOM_EMBULK_IMAGE = Variable.get("EMBULK_IMAGE", default_var="").strip()

    # # 공통 볼륨 설정
    # EMBULK_CONFIG_VOLUME = k8s.V1Volume(
    #     name="embulk-config-volume",
    #     config_map=k8s.V1ConfigMapVolumeSource(
    #         name="embulk-config",
    #         items=[k8s.V1KeyToPath(key="job.yml.liquid", path="job.yml.liquid")],
    #     ),
    # )
    EMBULK_CONFIG_MOUNT = k8s.V1VolumeMount(
        name="embulk-config-volume",
        mount_path="/app/config",
        read_only=True
    )

    @staticmethod
    def _generate_embulk_cmd(db_mount_path):
        return f"""
set -eu
export DB_HOST="$(cat {db_mount_path}/host)"
export DB_PORT="$(cat {db_mount_path}/port)"
export DB_USER="$(cat {db_mount_path}/user)"
export DB_PASSWORD="$(cat {db_mount_path}/password)"
export DB_DATABASE="$(cat {db_mount_path}/database)"
embulk run /app/config/job.yml.liquid
"""

    @staticmethod
    def _pick_conn_id(context, default_conn_id: str):
        params = context.get("params") or {}
        run_conf = getattr(context.get("dag_run"), "conf", {}) or {}
        return (
                params.get("slack_webhook_conn_id")
                or run_conf.get("slack_webhook_conn_id")
                or default_conn_id
        )

    @staticmethod
    def _send_slack_via_requests(message, conn_id):
        try:
            conn = BaseHook.get_connection(conn_id)
            token = conn.get_password()
            # 토큰이 전체 URL인 경우와 뒷부분만 있는 경우 모두 대응
            url = token if token.startswith("http") else f"https://hooks.slack.com/services/{token}"

            data = {"username": "Airflow", "text": message}
            res = requests.post(url, json=data, timeout=10)
            print(f"[SLACK_DEBUG] Response Status: {res.status_code}, Body: {res.text}")
            res.raise_for_status()
        except Exception as e:
            print(f"[SLACK_DEBUG] HTTP Post Error: {e}")

    # --- [메인 콜백 함수] ---
    @staticmethod
    def on_failure_slack(slack_conn_id='slack-dataops-alert-test'):
        def callback(context):

            try:
                print(f"[SLACK_DEBUG] Callback started for task: {context.get('task_instance').task_id}")

                ti = context.get("ti") or context.get("task_instance")
                dag_id = context.get("dag").dag_id if context.get("dag") else "unknown"
                task_id = getattr(ti, "task_id", "unknown")

                # 1. HyperDX용 유닉스 타임스탬프 계산 (ms)
                start_time = ti.start_date or context.get('logical_date')
                end_time = ti.end_date or pendulum.now()

                start_time = pendulum.instance(start_time)
                end_time = pendulum.instance(end_time)

                start_ms = int(start_time.subtract(minutes=5).timestamp() * 1000)
                end_ms = int(end_time.add(minutes=5).timestamp() * 1000)

                # 3. KST 시간 포맷팅
                logical_date = context.get('logical_date') or pendulum.now()
                execution_time_kst = pendulum.instance(logical_date).in_timezone("Asia/Seoul").strftime('%Y-%m-%d %H:%M:%S')

                # 3. HyperDX Log URL 구성
                log_url = (
                    f"https://hyperdx.data.com/dashboards/68f9e6fd39968b3fc16d236a"
                    f"?from={start_ms}&to={end_ms}"
                    f"&where=ResourceAttributes%5B%27k8s.pod.name%27%5D+LIKE+%27{dag_id.lower().replace('_', '-')}%25%27+"
                    f"AND+ResourceAttributes%5B%27k8s.container.name%27%5D=%27base%27+"
                    f"OR+ResourceAttributes%5B%27k8s.container.name%27%5D+LIKE+%27{task_id}%25%27"
                    f"&whereLanguage=sql"
                )

                # 4. 메시지 본문 작성 (사용자 포맷 기반)
                message = (
                    f":x: *Task Failed Alert*\n"
                    f"*DAG*: `{dag_id}`\n"
                    f"*Task*: `{task_id}`\n"
                    f"*Execution Time (KST)*: {execution_time_kst}\n"
                    f"*HyperDX Log*: <{log_url}|[View Logs]>\n"
                )

                # 5. 발송
                conn_id = EmbulkDagFactory._pick_conn_id(context, slack_conn_id)
                EmbulkDagFactory._send_slack_via_requests(message, conn_id)

            except Exception as e:
                print(f"[Slack Callback Error] {e}")

        return callback

    @classmethod
    def create_dag(cls,
                   dag_id,
                   schedule,
                   start_date,
                   dataset_info,
                   slack_conn_id,
                   db_secret_name,
                   db_mount_path,
                   slack_channel='',
                   partitioning=None,  # partitioning 파라미터 추가
                   tags=None,
                   custom_args=None,
                   ):

        default_args = {
            'owner': 'airflow',
            'retries': 1,
            'retry_delay': timedelta(minutes=5),
            'on_failure_callback': cls.on_failure_slack(slack_conn_id),
        }

        if custom_args:
            default_args.update(custom_args)

        db_secret = Secret(deploy_type="volume", deploy_target=db_mount_path, secret=db_secret_name)
        bq_secret = Secret(deploy_type="volume", deploy_target="/var/secrets/bq", secret="bq-sa-key")

        run_cmd = cls._generate_embulk_cmd(db_mount_path)

        dag = DAG(
            dag_id=dag_id,
            default_args=default_args,
            schedule=schedule,
            start_date=start_date,
            catchup=False,
            tags=tags or [],
            max_active_tasks=6,
        )

        with dag:
            all_tasks = []
            for info in dataset_info:
                manager = info['manager']
                dataset_name = info['dataset']
                table_prefix = info.get('prefix', '')

                jobs = manager.get_jobs()

                for job in jobs:
                    task = cls._add_k8s_task(
                        dag=dag,
                        job=job,
                        dataset_name=dataset_name,
                        table_prefix=table_prefix,
                        db_secret=db_secret,
                        bq_secret=bq_secret,
                        run_cmd=run_cmd
                    )
                    all_tasks.append(task)

            done_gate = EmptyOperator(task_id='done_all_embulk_tasks')

            if all_tasks:
                all_tasks >> done_gate

        return dag, done_gate

    @classmethod
    def _add_k8s_task(cls, dag, job, dataset_name, table_prefix, db_secret, bq_secret, run_cmd):

        limits = {"cpu": job.cpu, "memory": f"{str(job.memory)}Gi"}

        prefix_part = f"{table_prefix}_" if table_prefix else ""

        query = job.query if job.query else (
            f"SELECT * FROM {job.source_table}" if job.full_scan else
            f"SELECT * FROM {job.source_table} WHERE created_at >= '{{{{ data_interval_start.in_timezone(\'Asia/Seoul\') | ds }}}} 00:00:00' "
            f"AND created_at < '{{{{ data_interval_end.in_timezone(\'Asia/Seoul\') | ds }}}} 00:00:00'"
        )

        if job.target_table:
            bq_table = job.target_table
        elif job.single_table:
            bq_table = f"{prefix_part}{job.source_table}"
        else:
            bq_table = f"{prefix_part}{job.source_table}_{{{{ data_interval_start.in_timezone('Asia/Seoul') | ds_nodash }}}}"

        env_vars = {
            "DB_QUERY": query,
            "BQ_MODE": job.mode,
            "BQ_DATASET": dataset_name,
            "BQ_TABLE": bq_table,
            "BQ_KEY_PATH": "/var/secrets/bq/key.json"
        }

        if job.partitioning:
            env_vars["PARTITIONING_TYPE"] = job.partitioning.get("partitioning_type", "")
            env_vars["PARTITIONING_FIELD"] = job.partitioning.get("partitioning_field", "")

        # 공통 볼륨 설정
        EMBULK_CONFIG_VOLUME = k8s.V1Volume(
            name="embulk-config-volume",
            config_map=k8s.V1ConfigMapVolumeSource(
                name="embulk-config",
                items=[k8s.V1KeyToPath(key="partitioning_job.yml.liquid" if job.partitioning else "job.yml.liquid",
                                       path="job.yml.liquid")],
            ),
        )

        return KubernetesPodOperator(
            task_id=f'{job.target_dataset}-{job.source_table}'.replace('_', '-'),
            name=f'{job.target_dataset}-{job.source_table}'.replace('_', '-'),
            base_container_name=f'{job.target_dataset}-{job.source_table}'.replace('_', '-'),
            dag=dag,
            namespace='airflow',
            is_delete_operator_pod=True,
            image=cls.CUSTOM_EMBULK_IMAGE,
            cmds=["/bin/sh", "-c"],
            arguments=[run_cmd],
            secrets=[db_secret, bq_secret],
            env_vars=env_vars,
            container_resources=k8s.V1ResourceRequirements(requests={"cpu": 1, "memory": "1Gi"}, limits=limits),
            volumes=[EMBULK_CONFIG_VOLUME],
            volume_mounts=[cls.EMBULK_CONFIG_MOUNT],
            get_logs=True,
            in_cluster=True,
        )