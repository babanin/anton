{{/*
Chart name, truncated to 63 chars.
*/}}
{{- define "anton.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name, truncated to 63 chars.
*/}}
{{- define "anton.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Target namespace.
*/}}
{{- define "anton.namespace" -}}
{{- default .Release.Namespace .Values.namespaceOverride }}
{{- end }}

{{/*
Chart label value.
*/}}
{{- define "anton.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to all resources.
*/}}
{{- define "anton.labels" -}}
helm.sh/chart: {{ include "anton.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels for a component. Call with (dict "context" $ "component" "ingester").
*/}}
{{- define "anton.selectorLabels" -}}
app.kubernetes.io/name: {{ include "anton.name" .context }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Full image reference. Call with (dict "image" .Values.ingester.image).
*/}}
{{- define "anton.image" -}}
{{- if .image.registry }}
{{- printf "%s/%s:%s" .image.registry .image.repository .image.tag }}
{{- else }}
{{- printf "%s:%s" .image.repository .image.tag }}
{{- end }}
{{- end }}

{{/*
RabbitMQ host (service DNS name within the cluster).
*/}}
{{- define "anton.rabbitmqHost" -}}
{{- printf "%s-rabbitmq" (include "anton.fullname" .) }}
{{- end }}

{{/*
Secret name — defaults to "anton-secrets" to match the hardcoded reference
in orchestrator/templates/base_job.yaml.j2.
*/}}
{{- define "anton.secretName" -}}
{{- default "anton-secrets" .Values.secrets.name }}
{{- end }}

{{/*
Runner namespace — where the orchestrator creates Jobs.
*/}}
{{- define "anton.runnerNamespace" -}}
{{- default (include "anton.namespace" .) .Values.orchestrator.runner.namespace }}
{{- end }}

{{/*
Runner image reference.
*/}}
{{- define "anton.runnerImage" -}}
{{- include "anton.image" (dict "image" .Values.orchestrator.runner.image) }}
{{- end }}
