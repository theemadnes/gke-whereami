{{/*
Expand the name of the chart.
*/}}
{{- define "whereami.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s%s" $name .Values.suffix | trunc 63 | trimSuffix "-" }}
{{- end }}

