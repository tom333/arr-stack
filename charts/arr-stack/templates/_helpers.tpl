{{/*
Common labels for arr-stack umbrella-owned objects (ConfigMaps for arrconf + configarr).
Per-alias app-template renders carry their own labels — this helper applies only
to objects authored directly in charts/arr-stack/templates/.
*/}}
{{- define "arr-stack.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: arr-stack
{{- end }}
