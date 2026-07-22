{{- define "llh.name" -}}
local-llm-hub
{{- end -}}

{{- define "llh.labels" -}}
app.kubernetes.io/name: {{ include "llh.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: local-llm-hub
{{- end -}}

{{- define "llh.image" -}}
{{ .repository }}:{{ .tag }}@{{ .digest }}
{{- end -}}
