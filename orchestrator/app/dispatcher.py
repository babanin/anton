import json
import logging
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from kubernetes import client as k8s_client, config as k8s_config

from app.config import settings
from app.models import AgentTask, RouterPlan

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class JobManager:
    def __init__(self) -> None:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        self._core = k8s_client.CoreV1Api()
        self._batch = k8s_client.BatchV1Api()
        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )

    def create_job(
        self,
        task_id: str,
        plan: RouterPlan,
        original_task: AgentTask,
    ) -> str:
        configmap_name = f"agent-ctx-{task_id}"
        job_name = f"agent-job-{task_id}"
        namespace = settings.k8s_namespace

        # 1. Create ConfigMap with task context
        context_data = {
            "task": original_task.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
        }
        configmap = k8s_client.V1ConfigMap(
            metadata=k8s_client.V1ObjectMeta(
                name=configmap_name,
                namespace=namespace,
                labels={"app": "agent-runner", "task-id": task_id},
            ),
            data={"task.json": json.dumps(context_data, indent=2, default=str)},
        )
        self._core.create_namespaced_config_map(namespace=namespace, body=configmap)
        logger.info(
            "ConfigMap created",
            extra={"task_id": task_id, "configmap": configmap_name},
        )

        # 2. Render Job manifest from Jinja2 template
        template = self._jinja.get_template("base_job.yaml.j2")
        rendered = template.render(
            job_name=job_name,
            namespace=namespace,
            task_id=task_id,
            template_id=plan.template_id.value,
            complexity=plan.complexity.value,
            configmap_name=configmap_name,
            agent_image=settings.agent_image,
        )
        job_manifest = yaml.safe_load(rendered)

        # 3. Submit Job
        self._batch.create_namespaced_job(namespace=namespace, body=job_manifest)
        logger.info(
            "Job submitted",
            extra={"task_id": task_id, "job": job_name, "namespace": namespace},
        )
        return job_name
