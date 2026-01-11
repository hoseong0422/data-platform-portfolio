import yaml
from pathlib import Path
from dataclasses import dataclass, fields
from typing import Optional, List, Literal

from dataclasses import dataclass

@dataclass
class Job:
    source_table: str
    target_dataset: str = 'airflow_test'
    target_table: Optional[str] = None
    full_scan: bool = False
    single_table: bool = False
    memory: float = 1.0
    cpu: float = 1.0
    query: Optional[str] = None
    mode: Literal["replace", "append"] = "replace"
    partitioning: Optional[dict] = None

class Task:
    def __init__(self, caller_file: str):
        self.config_path = self._get_config_path(caller_file)
        self.raw_config = self._load_yaml()
        self.valid_job_fields = {f.name for f in fields(Job)}

    def _get_config_path(self, caller_file: str, config_folder: str = "config") -> Path:
        current_path = Path(caller_file).resolve()
        return current_path.parent / config_folder / f"{current_path.stem}.yml"

    def _load_yaml(self) -> dict:
        path = self.config_path
        if not path.exists():
            path = path.with_suffix(".yaml")

        if not path.exists():
            raise FileNotFoundError(f"YAML 설정을 찾을 수 없습니다: {self.config_path}")

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get_jobs(self, config_key: str = "embulk_tasks") -> List[Job]:
        jobs = []
        tasks_data = self.raw_config.get(config_key, [])

        for task_info in tasks_data:
            params = task_info.copy()

            if "source_table" not in params:
                continue

            if "query" in params and isinstance(params["query"], str):
                params["query"] = params["query"].replace("\n", " ").strip()
                
            filtered_params = {
                k: v for k, v in params.items() if k in self.valid_job_fields
            }

            jobs.append(Job(**filtered_params))

        return jobs