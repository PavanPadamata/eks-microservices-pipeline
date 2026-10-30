{{/* All helpers take a dict: root (the top-level context), name (service key), svc (its values). */}}

{{- define "ms.fullname" -}}
{{- printf "%s-%s" .root.Release.Name .name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ms.selectorLabels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end -}}

{{- define "ms.labels" -}}
{{ include "ms.selectorLabels" . }}
app.kubernetes.io/part-of: {{ .root.Chart.Name }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .root.Chart.Name .root.Chart.Version | replace "+" "_" }}
{{- end -}}
