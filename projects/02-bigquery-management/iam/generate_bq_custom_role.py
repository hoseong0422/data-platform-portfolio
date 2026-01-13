from typing import List, Optional
import sys
import subprocess
import json
import googleapiclient.discovery
import google.auth
from google.api_core.exceptions import AlreadyExists, FailedPrecondition
from google.cloud.iam_admin_v1 import CreateRoleRequest, IAMClient, Role
from typing import List, Optional


def create_role(
    project_id: str, role_id: str, permissions: List[str], title: Optional[str] = None, discription: Optional[str] = None
) -> Role:
    """Creates iam role with given parameters.

    Args:
        project_id: GCP project id
        role_id: id of GCP iam role
        permissions: list of iam permissions to assign to role. f.e ["iam.roles.get", "iam.roles.list"]
        title: title for iam role. role_id will be used in case of None
        description: description for custom iam role.

    Returns: google.cloud.iam_admin_v1.Role object
    """
    client = IAMClient()

    parent = f"projects/{project_id}"

    request = CreateRoleRequest(
        parent=parent,
        role_id=role_id,
        role=Role(title=title,
                  included_permissions=permissions,
                  description=description),
    )
    try:
        role = client.create_role(request)
        print(f"Created iam role: {role_id}: {role}")
        return role
    except AlreadyExists:
        print(f"Role with id [{role_id}] already exists, take some actions")
    except FailedPrecondition:
        print(
            f"Role with id [{role_id}] already exists and in deleted state, take some actions"
        )

def get_predefined_role_permissions_via_gcloud(role_name):
    """
    미리 정의된 GCP 역할이 포함하는 모든 개별 권한 목록을 gcloud CLI를 통해 가져옵니다.
    """
    try:
        # gcloud CLI 경로 확인 (환경에 따라 'gcloud'만으로 실행될 수도 있음)
        gcloud_path = subprocess.run(['which', 'gcloud'], capture_output=True, text=True, check=False).stdout.strip()
        if not gcloud_path:
            print("오류: 'gcloud' CLI를 찾을 수 없습니다. PATH 설정을 확인하세요.", file=sys.stderr)
            return []

        cmd = [gcloud_path, 'iam', 'roles', 'describe', role_name, '--format=json']

        # 명령 실행
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        role_info = json.loads(result.stdout)

        return role_info.get('includedPermissions', [])

    except subprocess.CalledProcessError as e:
        print(f"오류: gcloud CLI로 '{role_name}' 역할의 권한을 가져오는 데 실패했습니다.", file=sys.stderr)
        print(f"  Stdout: {e.stdout}", file=sys.stderr)
        print(f"  Stderr: {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"오류: gcloud CLI 출력 파싱 실패. {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"예상치 못한 오류: gcloud CLI를 통해 권한 가져오기 실패. {e}", file=sys.stderr)
        return []

def get_predefined_role_permissions_via_api(role_name):
    """
    미리 정의된 GCP 역할이 포함하는 모든 개별 권한 목록을 IAM API를 통해 가져옵니다.
    """
    try:
        credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        iam_service = googleapiclient.discovery.build('iam', 'v1', credentials=credentials)

        # iam_service 객체에 'roles' 속성이 있는지 확인
        if not hasattr(iam_service, 'roles') or not callable(iam_service.roles):
            print(f"경고: IAM API 클라이언트가 'roles()' 메서드를 제공하지 않습니다. gcloud CLI 폴백을 시도합니다.", file=sys.stderr)
            return None # None을 반환하여 폴백 트리거

        request = iam_service.roles().get(name=role_name)
        response = request.execute()

        return response.get('includedPermissions', [])
    except Exception as e:
        print(f"오류: IAM API로 '{role_name}' 역할의 권한을 가져오는 데 실패했습니다. {e}", file=sys.stderr)
        return None # None을 반환하여 폴백 트리거

def get_predefined_role_permissions(role_name):
    """
    미리 정의된 GCP 역할의 권한을 가져옵니다. API를 먼저 시도하고, 실패 시 gcloud CLI로 폴백합니다.
    """
    permissions = get_predefined_role_permissions_via_api(role_name)
    if permissions is None: # API 호출이 실패했거나 'roles' 속성이 없었을 경우
        print(f"API 호출 실패로 gcloud CLI를 통해 '{role_name}' 권한을 가져오는 중...", file=sys.stderr)
        permissions = get_predefined_role_permissions_via_gcloud(role_name)

    return permissions

def get_permissions(title, base_roles):

    all_permissions_for_custom_role = set()
    print(f"--- '{title}' 역할의 권한을 수집 중... ---")

    for base_role in base_roles:
        permissions = get_predefined_role_permissions(base_role)
        if permissions:
            print(f"  '{base_role}'에서 {len(permissions)}개의 권한 추가.")
            if 'resourcemanager.projects.list' in permissions:
                permissions.remove('resourcemanager.projects.list')

            if 'bigquery.rowAccessPolicies.overrideTimeTravelRestrictions' in permissions:
                permissions.remove('bigquery.rowAccessPolicies.overrideTimeTravelRestrictions')

            if 'editor' in title.lower():
                all_permissions_for_custom_role.update(['bigquery.transfers.update'])

            all_permissions_for_custom_role.update(permissions)
        else:
            print(f"  경고: '{base_role}'의 권한을 가져오는 데 실패했습니다. 이 역할은 커스텀 역할에 포함되지 않을 수 있습니다.", file=sys.stderr)
    return all_permissions_for_custom_role

if __name__ == '__main__':

    custom_roles = [
        {
            'role_id': 'bigquery.admin',
            'title': 'BigQuery-Admin',
            'description': 'Custom role with broad BigQuery administrative capabilities.',
            'base_roles': [
                'roles/bigquery.admin',
                'roles/iam.serviceAccountUser'
            ]
        },
        {
            'role_id': 'bigquery.editor',
            'title': 'BigQuery-Editor',
            'description': 'Custom role for BigQuery data editing and viewing.',
            'base_roles': [
                'roles/bigquery.dataEditor',
                'roles/bigquery.user',
                'roles/bigquery.metadataViewer',
                'roles/iam.serviceAccountUser'
            ]
        },
        {
            'role_id': 'bigquery.user',
            'title': 'BigQuery-User',
            'description': 'Custom role for basic BigQuery usage, viewing, and job execution.',
            'base_roles': [
                'roles/bigquery.dataViewer',
                'roles/bigquery.user'
            ]
        }
    ]

    project_id = 'project_id' # 변경 필요

    for custom_role in custom_roles:
        title = custom_role['title']
        role_id = custom_role['role_id']
        base_roles = custom_role['base_roles']
        description = custom_role['description']

        permissions = list(get_permissions(title, base_roles))

        create_role(
            project_id,
            role_id,
            permissions,
            title,
            description
        )
